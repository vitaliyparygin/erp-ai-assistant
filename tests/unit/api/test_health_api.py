import httpx
from app.api.v1.health import (
    _check_postgres,
    _check_qdrant,
    _check_redis,
    _check_ollama,
)
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.api.v1 import health
# ----------------------------------------------------------------------
# liveness
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_liveness():
    settings = SimpleNamespace(app_version="1.2.3")

    result = await health.liveness(settings)

    assert result == {
        "status": "alive",
        "version": "1.2.3",
    }


# ----------------------------------------------------------------------
# readiness
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_readiness_all_healthy(monkeypatch):
    monkeypatch.setattr(
        health,
        "_check_postgres",
        AsyncMock(
            return_value=health.ServiceHealth(service="postgres", status="healthy")
        ),
    )
    monkeypatch.setattr(
        health,
        "_check_redis",
        AsyncMock(return_value=health.ServiceHealth(service="redis", status="healthy")),
    )
    monkeypatch.setattr(
        health,
        "_check_qdrant",
        AsyncMock(
            return_value=health.ServiceHealth(service="qdrant", status="healthy")
        ),
    )
    monkeypatch.setattr(
        health,
        "_check_ollama",
        AsyncMock(
            return_value=health.ServiceHealth(service="ollama", status="healthy")
        ),
    )

    settings = SimpleNamespace(
        app_version="1.0.0",
        qdrant_collection_name="erp_documents",
        ollama_base_url="http://ollama",
    )

    result = await health.readiness(
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        settings,
    )

    assert result.status == "healthy"
    assert len(result.services) == 4


@pytest.mark.asyncio
async def test_readiness_degraded(monkeypatch):
    monkeypatch.setattr(
        health,
        "_check_postgres",
        AsyncMock(
            return_value=health.ServiceHealth(service="postgres", status="healthy")
        ),
    )
    monkeypatch.setattr(
        health,
        "_check_redis",
        AsyncMock(
            return_value=health.ServiceHealth(service="redis", status="unhealthy")
        ),
    )
    monkeypatch.setattr(
        health,
        "_check_qdrant",
        AsyncMock(
            return_value=health.ServiceHealth(service="qdrant", status="healthy")
        ),
    )
    monkeypatch.setattr(
        health,
        "_check_ollama",
        AsyncMock(
            return_value=health.ServiceHealth(service="ollama", status="healthy")
        ),
    )

    settings = SimpleNamespace(
        app_version="1",
        qdrant_collection_name="erp_documents",
        ollama_base_url="http://ollama",
    )

    result = await health.readiness(
        AsyncMock(),
        AsyncMock(),
        AsyncMock(),
        settings,
    )

    assert result.status == "degraded"


# ----------------------------------------------------------------------
# full_health
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_health_healthy():
    db = AsyncMock()

    result = MagicMock()
    result.scalar.return_value = 5
    db.execute.return_value = result

    redis = AsyncMock()
    redis.info.return_value = {
        "used_memory_human": "10M",
        "maxmemory_human": "100M",
    }
    redis.dbsize.return_value = 3

    qdrant = AsyncMock()

    collection = MagicMock()
    collection.name = "erp_documents"

    collections = MagicMock()
    collections.collections = [collection]
    qdrant.get_collections.return_value = collections

    collection_info = MagicMock()
    collection_info.points_count = 10
    collection_info.indexed_vectors_count = 10
    collection_info.status = "green"

    qdrant.get_collection.return_value = collection_info

    settings = SimpleNamespace(
        app_version="1",
        qdrant_collection_name="erp_documents",
        ollama_base_url="http://ollama",
        langfuse_enabled=False,
    )

    health._check_ollama = AsyncMock(
        return_value=health.ServiceHealth(
            service="ollama",
            status="healthy",
        )
    )

    response = await health.full_health(
        db,
        redis,
        qdrant,
        settings,
    )

    assert response.status == "healthy"
    assert len(response.services) == 4


@pytest.mark.asyncio
async def test_full_health_unhealthy_postgres():
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("db down")

    redis = AsyncMock()
    redis.info.return_value = {}
    redis.dbsize.return_value = 0

    qdrant = AsyncMock()

    collections = MagicMock()
    collections.collections = []

    qdrant.get_collections.return_value = collections

    settings = SimpleNamespace(
        app_version="1",
        qdrant_collection_name="erp_documents",
        ollama_base_url="http://ollama",
        langfuse_enabled=False,
    )

    health._check_ollama = AsyncMock(
        return_value=health.ServiceHealth(
            service="ollama",
            status="healthy",
        )
    )

    response = await health.full_health(
        db,
        redis,
        qdrant,
        settings,
    )

    assert response.status == "unhealthy"


@pytest.mark.asyncio
async def test_full_health_langfuse_enabled():
    db = AsyncMock()

    result = MagicMock()
    result.scalar.return_value = 1
    db.execute.return_value = result

    redis = AsyncMock()
    redis.info.return_value = {}
    redis.dbsize.return_value = 0

    qdrant = AsyncMock()

    collections = MagicMock()
    collections.collections = []

    qdrant.get_collections.return_value = collections

    settings = SimpleNamespace(
        app_version="1",
        qdrant_collection_name="erp_documents",
        ollama_base_url="http://ollama",
        langfuse_enabled=True,
        langfuse_secret_key="secret",
        langfuse_public_key="public",
        langfuse_host="http://langfuse",
    )

    health._check_ollama = AsyncMock(
        return_value=health.ServiceHealth(
            service="ollama",
            status="healthy",
        )
    )

    response = await health.full_health(
        db,
        redis,
        qdrant,
        settings,
    )

    assert any(s.service == "langfuse" for s in response.services)


@pytest.mark.asyncio
async def test_full_health_langfuse_degraded():
    db = AsyncMock()

    result = MagicMock()
    result.scalar.return_value = 1
    db.execute.return_value = result

    redis = AsyncMock()
    redis.info.return_value = {}
    redis.dbsize.return_value = 0

    qdrant = AsyncMock()

    collections = MagicMock()
    collections.collections = []

    qdrant.get_collections.return_value = collections

    settings = SimpleNamespace(
        app_version="1",
        qdrant_collection_name="erp_documents",
        ollama_base_url="http://ollama",
        langfuse_enabled=True,
        langfuse_secret_key=None,
        langfuse_public_key=None,
        langfuse_host="http://langfuse",
    )

    health._check_ollama = AsyncMock(
        return_value=health.ServiceHealth(
            service="ollama",
            status="healthy",
        )
    )

    response = await health.full_health(
        db,
        redis,
        qdrant,
        settings,
    )

    langfuse = next(s for s in response.services if s.service == "langfuse")

    assert langfuse.status == "degraded"


# ------------------------------------------------------------------
# _check_postgres
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_postgres_success():
    db = AsyncMock()

    result = await _check_postgres(db)

    db.execute.assert_awaited_once()
    assert result.service == "postgres"
    assert result.status == "healthy"
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_check_postgres_failure():
    db = AsyncMock()
    db.execute.side_effect = RuntimeError("db down")

    result = await _check_postgres(db)

    assert result.service == "postgres"
    assert result.status == "unhealthy"
    assert "db down" in result.details["error"]


# ------------------------------------------------------------------
# _check_redis
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_redis_success():
    redis = AsyncMock()
    redis.info.return_value = {
        "used_memory_human": "10M",
    }

    result = await _check_redis(redis)

    redis.ping.assert_awaited_once()
    redis.info.assert_awaited_once_with("memory")

    assert result.service == "redis"
    assert result.status == "healthy"
    assert result.details["used_memory_human"] == "10M"


@pytest.mark.asyncio
async def test_check_redis_failure():
    redis = AsyncMock()
    redis.ping.side_effect = RuntimeError("redis down")

    result = await _check_redis(redis)

    assert result.service == "redis"
    assert result.status == "unhealthy"
    assert "redis down" in result.details["error"]


# ------------------------------------------------------------------
# _check_qdrant
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_qdrant_success():
    client = AsyncMock()

    collection = MagicMock()
    collection.name = "erp_documents"

    collections = MagicMock()
    collections.collections = [collection]

    client.get_collections.return_value = collections

    result = await _check_qdrant(client, "erp_documents")

    client.get_collections.assert_awaited_once()

    assert result.service == "qdrant"
    assert result.status == "healthy"
    assert result.details["collections"] == ["erp_documents"]
    assert result.details["target_collection_exists"] is True


@pytest.mark.asyncio
async def test_check_qdrant_collection_missing():
    client = AsyncMock()

    collection = MagicMock()
    collection.name = "other"

    collections = MagicMock()
    collections.collections = [collection]

    client.get_collections.return_value = collections

    result = await _check_qdrant(client, "erp_documents")

    assert result.status == "healthy"
    assert result.details["target_collection_exists"] is False


@pytest.mark.asyncio
async def test_check_qdrant_failure():
    client = AsyncMock()
    client.get_collections.side_effect = RuntimeError("qdrant down")

    result = await _check_qdrant(client, "erp_documents")

    assert result.service == "qdrant"
    assert result.status == "unhealthy"
    assert "qdrant down" in result.details["error"]


# ------------------------------------------------------------------
# _check_ollama
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_ollama_success(monkeypatch):
    response = MagicMock(status_code=200)

    client = AsyncMock()
    client.get.return_value = response

    cm = AsyncMock()
    cm.__aenter__.return_value = client

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: cm)

    result = await _check_ollama("http://ollama")

    client.get.assert_awaited_once_with("http://ollama/api/tags")

    assert result.service == "ollama"
    assert result.status == "healthy"


@pytest.mark.asyncio
async def test_check_ollama_bad_status(monkeypatch):
    response = MagicMock(status_code=503)

    client = AsyncMock()
    client.get.return_value = response

    cm = AsyncMock()
    cm.__aenter__.return_value = client

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: cm)

    result = await _check_ollama("http://ollama")

    assert result.status == "unhealthy"


@pytest.mark.asyncio
async def test_check_ollama_exception(monkeypatch):
    client = AsyncMock()
    client.get.side_effect = RuntimeError("connection refused")

    cm = AsyncMock()
    cm.__aenter__.return_value = client

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: cm)

    result = await _check_ollama("http://ollama")

    assert result.service == "ollama"
    assert result.status == "unhealthy"
    assert "connection refused" in result.details["error"]
