import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from app.main import app
from unittest.mock import MagicMock
from app.core.dependencies import (
    get_db_session,
    get_redis_client,
    get_settings,
    get_qdrant_client,
)
from app.models.schemas import ServiceHealth
from tests.factories import make_settings
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_liveness():

    async def override_settings():
        return make_settings()

    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_readiness_ok(monkeypatch):
    ok = ServiceHealth(
        service="postgres",
        status="ok",
        latency_ms=1,
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_postgres",
        AsyncMock(return_value=ok),
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_redis",
        AsyncMock(return_value=ok),
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_qdrant",
        AsyncMock(return_value=ok),
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_ollama",
        AsyncMock(return_value=ok),
    )

    async def override_db():
        yield AsyncMock()

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    async def override_settings():
        return make_settings()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_readiness_failed(monkeypatch):
    ok = ServiceHealth(
        service="postgres",
        status="ok",
        latency_ms=1,
    )

    failed = ServiceHealth(
        service="redis",
        status="error",
        latency_ms=None,
        error="boom",
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_postgres",
        AsyncMock(return_value=ok),
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_redis",
        AsyncMock(return_value=failed),
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_qdrant",
        AsyncMock(return_value=ok),
    )

    monkeypatch.setattr(
        "app.api.v1.health._check_ollama",
        AsyncMock(return_value=ok),
    )

    async def override_db():
        yield AsyncMock()

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    async def override_settings():
        return make_settings()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"


@pytest.mark.asyncio
async def test_full_health():
    #
    # Database
    #
    db = AsyncMock()

    count_result = MagicMock()
    count_result.scalar.return_value = 10

    db.execute.return_value = count_result

    #
    # Redis
    #
    redis = AsyncMock()
    redis.ping.return_value = True
    redis.info.return_value = {
        "used_memory_human": "10MB",
        "maxmemory_human": "100MB",
    }
    redis.dbsize.return_value = 5

    #
    # Qdrant
    #
    qdrant = AsyncMock()

    qdrant.get_collections.return_value = SimpleNamespace(
        collections=[
            SimpleNamespace(name="documents"),
        ]
    )

    qdrant.get_collection.return_value = SimpleNamespace(
        points_count=123,
        indexed_vectors_count=123,
        status="green",
    )

    #
    # Settings
    #
    settings = make_settings()
    settings.qdrant_collection_name = "documents"
    settings.langfuse_enabled = False

    #
    # Ollama
    #
    async def fake_ollama(_):
        from app.models.schemas import ServiceHealth

        return ServiceHealth(
            service="ollama",
            status="healthy",
        )

    #
    # Overrides
    #
    async def override_db():
        yield db

    async def override_redis():
        yield redis

    async def override_qdrant():
        yield qdrant

    async def override_settings():
        return settings

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant
    app.dependency_overrides[get_settings] = override_settings

    from app.api.v1 import health

    original = health._check_ollama
    health._check_ollama = fake_ollama

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/v1/health/",
                follow_redirects=True,
            )
    finally:
        health._check_ollama = original
        app.dependency_overrides.clear()

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "healthy"

    services = {s["service"]: s for s in body["services"]}

    assert services["postgres"]["status"] == "healthy"
    assert services["redis"]["status"] == "healthy"
    assert services["qdrant"]["status"] == "healthy"
    assert services["ollama"]["status"] == "healthy"
