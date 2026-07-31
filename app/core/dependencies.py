"""
FastAPI dependency injection.
Provides reusable dependencies for database sessions, caches,
vector stores, and service instances.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.observability.langfuse_client import get_langfuse_client

logger = get_logger(__name__)
security = HTTPBearer(auto_error=False)


# =============================================================================
# Settings
# =============================================================================

SettingsDep = Annotated[Settings, Depends(get_settings)]


# =============================================================================
# Database Session
# =============================================================================


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# =============================================================================
# Redis
# =============================================================================


async def get_redis_client(
    settings: SettingsDep,
) -> AsyncGenerator[aioredis.Redis, None]:  # type: ignore[type-arg]
    """Provide a Redis client from the connection pool."""
    client = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )
    try:
        yield client
    finally:
        await client.aclose()


RedisDep = Annotated[aioredis.Redis, Depends(get_redis_client)]  # type: ignore[type-arg]


# =============================================================================
# Qdrant
# =============================================================================


async def get_qdrant_client(
    settings: SettingsDep,
) -> AsyncGenerator[AsyncQdrantClient, None]:
    """Provide an async Qdrant client."""
    client = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
        timeout=30,
    )
    try:
        yield client
    finally:
        await client.close()


QdrantDep = Annotated[AsyncQdrantClient, Depends(get_qdrant_client)]


# =============================================================================
# Rate Limiting
# =============================================================================


async def check_rate_limit(
    request: Request,
    redis: RedisDep,
    settings: SettingsDep,
) -> None:
    """
    Token-bucket rate limiter using Redis.
    Limits requests per IP address per time window.
    """
    if not settings.rate_limit_enabled:
        return

    client_ip = request.client.host if request.client else "unknown"
    key = f"rate_limit:{client_ip}"

    async with redis.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, settings.rate_limit_window)
        results = await pipe.execute()

    request_count = results[0]
    if request_count > settings.rate_limit_requests:
        raise RateLimitError(
            f"Rate limit exceeded: {request_count}/{settings.rate_limit_requests} "
            f"requests in {settings.rate_limit_window}s"
        )


RateLimitDep = Depends(check_rate_limit)


# =============================================================================
# Authentication (Optional — JWT)
# =============================================================================


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict | None:
    """
    Optionally authenticate the request.
    Returns user payload if authenticated, None otherwise.
    """
    if credentials is None:
        return None

    try:
        from jose import jwt

        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=["HS256"],
        )
        return payload
    except Exception:
        import traceback

        traceback.print_exc()
        raise


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Require authentication. Raises 401 if not authenticated."""
    user = await get_current_user_optional(credentials, settings)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUserDep = Annotated[dict, Depends(get_current_user)]
CurrentUserOptionalDep = Annotated[dict | None, Depends(get_current_user_optional)]


# =============================================================================
# Observability
# =============================================================================


async def get_trace_client(settings: SettingsDep):  # type: ignore[return]
    """Provide the LangFuse tracing client."""
    return get_langfuse_client(settings)
