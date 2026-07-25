"""
Health check endpoints.
Provides liveness, readiness, and deep dependency checks.
Used by Docker healthchecks, load balancers, and monitoring systems.
"""
import time
from typing import Any
import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.dependencies import DBSessionDep, QdrantDep, RedisDep, SettingsDep
from app.core.logging import get_logger
from app.models.schemas import HealthResponse, ServiceHealth

router = APIRouter()
logger = get_logger(__name__)


async def _check_postgres(db: AsyncSession) -> ServiceHealth:
    start = time.monotonic()
    try:
        await db.execute(text("SELECT 1"))
        return ServiceHealth(
            service="postgres",
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
        )
    except Exception as e:
        logger.error("health_postgres_failed", error=str(e))
        return ServiceHealth(service="postgres", status="unhealthy", details={"error": str(e)})


async def _check_redis(redis: aioredis.Redis) -> ServiceHealth:  # type: ignore[type-arg]
    start = time.monotonic()
    try:
        await redis.ping()
        info = await redis.info("memory")
        return ServiceHealth(
            service="redis",
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
            details={"used_memory_human": info.get("used_memory_human", "unknown")},
        )
    except Exception as e:
        logger.error("health_redis_failed", error=str(e))
        return ServiceHealth(service="redis", status="unhealthy", details={"error": str(e)})


async def _check_qdrant(qdrant: AsyncQdrantClient, collection: str) -> ServiceHealth:
    start = time.monotonic()
    try:
        collections = await qdrant.get_collections()
        names = [c.name for c in collections.collections]
        return ServiceHealth(
            service="qdrant",
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
            details={
                "collections": names,
                "target_collection_exists": collection in names,
            },
        )
    except Exception as e:
        logger.error("health_qdrant_failed", error=str(e))
        return ServiceHealth(service="qdrant", status="unhealthy", details={"error": str(e)})


async def _check_ollama(base_url: str) -> ServiceHealth:
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(f"{base_url}/api/tags")

        return ServiceHealth(
            service="ollama",
            status="healthy" if response.status_code == 200 else "unhealthy",
        )

    except Exception as e:
        return ServiceHealth(
            service="ollama",
            status="unhealthy",
            details={"error": str(e)},
        )


# =============================================================================
# Liveness probe — is the process alive?
# =============================================================================

@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 if the process is running. No dependency checks.",
    tags=["Health"],
)
async def liveness(settings: SettingsDep) -> dict[str, str]:
    return {"status": "alive", "version": settings.app_version}


# =============================================================================
# Readiness probe — can the service handle traffic?
# =============================================================================

@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns 200 only when all critical dependencies (Postgres, Redis, Qdrant) are reachable.",
    response_model=HealthResponse,
    tags=["Health"],
)
async def readiness(
    db: DBSessionDep,
    redis: RedisDep,
    qdrant: QdrantDep,
    settings: SettingsDep,
) -> HealthResponse:
    checks = [
        await _check_postgres(db),
        await _check_redis(redis),
        await _check_qdrant(qdrant, settings.qdrant_collection_name),
        await _check_ollama(settings.ollama_base_url),
    ]

    all_healthy = all(c.status == "healthy" for c in checks)
    overall = "healthy" if all_healthy else "degraded"

    logger.info("readiness_check", status=overall, services={c.service: c.status for c in checks})

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        services=checks,
    )


# =============================================================================
# Deep health — full dependency diagnostics
# =============================================================================

@router.get(
    "/",
    summary="Full health report",
    description="Detailed health status of every dependency with latencies.",
    response_model=HealthResponse,
    tags=["Health"],
)
async def full_health(
    db: DBSessionDep,
    redis: RedisDep,
    qdrant: QdrantDep,
    settings: SettingsDep,
) -> HealthResponse:
    checks: list[ServiceHealth] = []

    # Postgres — check row counts as a functional signal
    start = time.monotonic()
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM documents"))
        doc_count = result.scalar() or 0
        checks.append(ServiceHealth(
            service="postgres",
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
            details={"document_count": doc_count},
        ))
    except Exception as e:
        checks.append(ServiceHealth(
            service="postgres", status="unhealthy", details={"error": str(e)}
        ))

    # Redis — memory + keyspace stats
    start = time.monotonic()
    try:
        await redis.ping()
        info = await redis.info("memory")
        key_count = await redis.dbsize()
        checks.append(ServiceHealth(
            service="redis",
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
            details={
                "used_memory_human": info.get("used_memory_human"),
                "maxmemory_human": info.get("maxmemory_human"),
                "active_keys": key_count,
            },
        ))
    except Exception as e:
        checks.append(ServiceHealth(service="redis", status="unhealthy", details={"error": str(e)}))

    # Qdrant — collection info
    start = time.monotonic()
    try:
        col_name = settings.qdrant_collection_name
        collections = await qdrant.get_collections()
        names = [c.name for c in collections.collections]
        details: dict[str, Any] = {"collections": names}
        if col_name in names:
            col_info = await qdrant.get_collection(col_name)
            details["points_count"] = col_info.points_count
            details["indexed_vectors_count"] = col_info.indexed_vectors_count
            details["indexed_vectors"] = col_info.indexed_vectors_count
            details["status"] = col_info.status
        checks.append(ServiceHealth(
            service="qdrant",
            status="healthy",
            latency_ms=round((time.monotonic() - start) * 1000, 2),
            details=details,
        ))
    except Exception as e:
        checks.append(ServiceHealth(service="qdrant", status="unhealthy", details={"error": str(e)}))

    # OpenAI key
    checks.append(await _check_ollama(settings.ollama_base_url))

    # LangFuse (optional)
    if settings.langfuse_enabled:
        lf_ok = bool(settings.langfuse_secret_key and settings.langfuse_public_key)
        checks.append(ServiceHealth(
            service="langfuse",
            status="healthy" if lf_ok else "degraded",
            details={"configured": lf_ok, "host": settings.langfuse_host},
        ))

    unhealthy = [c for c in checks if c.status == "unhealthy"]
    degraded = [c for c in checks if c.status == "degraded"]
    if unhealthy:
        overall = "unhealthy"
    elif degraded:
        overall = "degraded"
    else:
        overall = "healthy"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        services=checks,
    )
