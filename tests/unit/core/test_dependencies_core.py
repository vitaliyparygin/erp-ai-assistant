import pytest
from unittest.mock import MagicMock, AsyncMock
from app.core import dependencies
from app.core.exceptions import RateLimitError
from fastapi import HTTPException
from app.core.dependencies import (
    get_current_user,
    get_current_user_optional,
    check_rate_limit,
    get_qdrant_client,
    get_redis_client,
)


class DummyPipeline:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def incr(self, *args, **kwargs):
        pass

    def expire(self, *args, **kwargs):
        pass

    async def execute(self):
        return [101, None]


@pytest.mark.asyncio
async def test_get_current_user_401(monkeypatch):
    monkeypatch.setattr(
        "app.core.dependencies.get_current_user_optional",
        AsyncMock(return_value=None),
    )

    with pytest.raises(HTTPException):
        await get_current_user(
            None,
            MagicMock(),
        )


@pytest.mark.asyncio
async def test_get_current_user(monkeypatch):
    monkeypatch.setattr(
        "app.core.dependencies.get_current_user_optional",
        AsyncMock(return_value={"sub": "1"}),
    )

    result = await get_current_user(
        None,
        MagicMock(),
    )

    assert result["sub"] == "1"


@pytest.mark.asyncio
async def test_get_current_user_optional_none():
    settings = MagicMock()

    result = await get_current_user_optional(
        None,
        settings,
    )

    assert result is None


@pytest.mark.asyncio
async def test_rate_limit_exceeded():
    request = MagicMock()
    request.client.host = "127.0.0.1"

    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[101, True])


    redis = MagicMock()
    redis.pipeline.return_value = DummyPipeline()

    settings = MagicMock(
        rate_limit_enabled=True,
        rate_limit_requests=100,
        rate_limit_window=60,
    )

    with pytest.raises(RateLimitError):
        await check_rate_limit(
            request,
            redis,
            settings,
        )


@pytest.mark.asyncio
async def test_rate_limit_disabled():
    request = MagicMock()
    redis = AsyncMock()

    settings = MagicMock(rate_limit_enabled=False)

    await check_rate_limit(
        request,
        redis,
        settings,
    )

    redis.pipeline.assert_not_called()


@pytest.mark.asyncio
async def test_get_qdrant_client_close(monkeypatch):
    client = AsyncMock()

    monkeypatch.setattr(
        "app.core.dependencies.AsyncQdrantClient",
        lambda **kwargs: client,
    )

    settings = MagicMock(
        qdrant_url="http://localhost",
        qdrant_api_key=None,
    )

    gen = get_qdrant_client(settings)

    await anext(gen)

    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_redis_client_close(monkeypatch):
    client = AsyncMock()

    monkeypatch.setattr(
        "redis.asyncio.from_url",
        lambda *args, **kwargs: client,
    )

    settings = MagicMock(redis_url="redis://localhost")

    gen = get_redis_client(settings)

    await anext(gen)

    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_rate_limit_unknown_client():
    request = AsyncMock()
    request.client = None

    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[5, True])

    class PipelineCtx:
        async def __aenter__(self):
            return pipe

        async def __aexit__(self, exc_type, exc, tb):
            return False

    redis = MagicMock()
    redis.pipeline.return_value = PipelineCtx()

    settings = AsyncMock()
    settings.rate_limit_enabled = True
    settings.rate_limit_requests = 10
    settings.rate_limit_window = 60

    await dependencies.check_rate_limit(
        request=request,
        redis=redis,
        settings=settings,
    )

    pipe.incr.assert_called_once_with("rate_limit:unknown")


@pytest.mark.asyncio
async def test_check_rate_limit_exceeded():
    request = AsyncMock()
    request.client.host = "127.0.0.1"

    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[15, True])

    class PipelineCtx:
        async def __aenter__(self):
            return pipe

        async def __aexit__(self, exc_type, exc, tb):
            return None

    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=PipelineCtx())

    settings = AsyncMock()
    settings.rate_limit_enabled = True
    settings.rate_limit_requests = 10
    settings.rate_limit_window = 60

    with pytest.raises(RateLimitError):
        await dependencies.check_rate_limit(
            request=request,
            redis=redis,
            settings=settings,
        )


@pytest.mark.asyncio
async def test_check_rate_limit_success():
    request = AsyncMock()
    request.client.host = "127.0.0.1"

    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[5, True])

    class PipelineCtx:
        async def __aenter__(self):
            return pipe

        async def __aexit__(self, exc_type, exc, tb):
            return None

    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=PipelineCtx())

    settings = AsyncMock()
    settings.rate_limit_enabled = True
    settings.rate_limit_requests = 10
    settings.rate_limit_window = 60

    await dependencies.check_rate_limit(
        request=request,
        redis=redis,
        settings=settings,
    )

    pipe.incr.assert_called_once_with("rate_limit:127.0.0.1")
    pipe.expire.assert_called_once_with("rate_limit:127.0.0.1", 60)
    pipe.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_rate_limit_disabled():
    request = AsyncMock()
    request.client.host = "127.0.0.1"

    redis = AsyncMock()

    settings = AsyncMock()
    settings.rate_limit_enabled = False

    await dependencies.check_rate_limit(
        request=request,
        redis=redis,
        settings=settings,
    )

    redis.pipeline.assert_not_called()


# -------------------------------------------------------------------
# get_db_session
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_session_commit(monkeypatch):
    session = AsyncMock()

    class FakeContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(
        dependencies,
        "AsyncSessionLocal",
        lambda: FakeContext(),
    )

    agen = dependencies.get_db_session()

    value = await agen.__anext__()

    assert value is session

    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()

    session.commit.assert_awaited_once()
    session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_db_session_rollback(monkeypatch):
    session = AsyncMock()

    class FakeContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(
        dependencies,
        "AsyncSessionLocal",
        lambda: FakeContext(),
    )

    agen = dependencies.get_db_session()

    await agen.__anext__()

    with pytest.raises(RuntimeError):
        await agen.athrow(RuntimeError("boom"))

    session.rollback.assert_awaited_once()


# -------------------------------------------------------------------
# get_redis_client
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_redis_client(monkeypatch):
    redis = AsyncMock()

    monkeypatch.setattr(
        dependencies.aioredis,
        "from_url",
        lambda *args, **kwargs: redis,
    )

    settings = AsyncMock()
    settings.redis_url = "redis://localhost"

    agen = dependencies.get_redis_client(settings)

    value = await agen.__anext__()

    assert value is redis

    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()

    redis.aclose.assert_awaited_once()


# -------------------------------------------------------------------
# get_qdrant_client
# -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_qdrant_client(monkeypatch):
    client = AsyncMock()

    monkeypatch.setattr(
        dependencies,
        "AsyncQdrantClient",
        lambda **kwargs: client,
    )

    settings = AsyncMock()
    settings.qdrant_url = "http://localhost"
    settings.qdrant_api_key = None

    agen = dependencies.get_qdrant_client(settings)

    value = await agen.__anext__()

    assert value is client

    with pytest.raises(StopAsyncIteration):
        await agen.__anext__()

    client.close.assert_awaited_once()
