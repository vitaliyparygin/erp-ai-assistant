from app.rag.embeddings import EmbeddingService
import json
from unittest.mock import MagicMock
import httpx
import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_call_ollama_embedding_http_error(monkeypatch):
    service = EmbeddingService()

    class Response:
        def raise_for_status(self):
            raise httpx.HTTPStatusError(
                "bad",
                request=MagicMock(),
                response=MagicMock(),
            )

    client = AsyncMock()
    client.post.return_value = Response()

    class DummyClient:
        async def __aenter__(self):
            return client

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: DummyClient())

    with pytest.raises(httpx.HTTPStatusError):
        await service._call_ollama_embedding(["abc"])


@pytest.mark.asyncio
async def test_call_ollama_embedding_multiple(monkeypatch):
    service = EmbeddingService()

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"embeddings": [[0.1, 0.2]]}

    client = AsyncMock()
    client.post.return_value = Response()

    class DummyClient:
        async def __aenter__(self):
            return client

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: DummyClient())

    result = await service._call_ollama_embedding(
        ["a", "b", "c"],
    )

    assert result == [
        [0.1, 0.2],
        [0.1, 0.2],
        [0.1, 0.2],
    ]

    assert client.post.await_count == 3


@pytest.mark.asyncio
async def test_cache_embedding_without_redis():
    service = EmbeddingService(redis_client=None)

    await service._cache_embedding("abc", [1.0, 2.0])


@pytest.mark.asyncio
async def test_get_cached_embedding_without_redis():
    service = EmbeddingService(redis_client=None)

    result = await service._get_cached_embedding("abc")

    assert result is None


def test_cache_key_changes_with_dimensions():
    service = EmbeddingService()

    service._model = "same"

    service._dimensions = 768
    key1 = service._cache_key("hello")

    service._dimensions = 1024
    key2 = service._cache_key("hello")

    assert key1 != key2


def test_cache_key_changes_with_model():
    service = EmbeddingService()

    service._model = "model-a"
    key1 = service._cache_key("hello")

    service._model = "model-b"
    key2 = service._cache_key("hello")

    assert key1 != key2


@pytest.mark.asyncio
async def test_cache_embedding_redis_failure():
    redis = AsyncMock()
    redis.setex.side_effect = RuntimeError("redis error")

    service = EmbeddingService(redis)

    # метод лише логує помилку
    await service._cache_embedding("abc", [1.0])


@pytest.mark.asyncio
async def test_get_cached_embedding_invalid_json():
    redis = AsyncMock()
    redis.get.return_value = "not-json"

    service = EmbeddingService(redis)

    with pytest.raises(Exception):
        await service._get_cached_embedding("abc")


@pytest.mark.asyncio
async def test_call_ollama_embedding_success(monkeypatch):
    responses = []

    for value in ([1.0], [2.0]):
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "embeddings": [value],
        }
        responses.append(response)

    client = AsyncMock()
    client.post.side_effect = responses

    class ClientCtx:
        async def __aenter__(self):
            return client

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kwargs: ClientCtx(),
    )

    service = EmbeddingService(redis_client=None)

    result = await service._call_ollama_embedding(
        ["one", "two"],
    )

    assert result == [
        [1.0],
        [2.0],
    ]


@pytest.mark.asyncio
async def test_embed_text_empty_embeddings(monkeypatch):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "embeddings": [],
    }

    client = AsyncMock()
    client.post.return_value = response

    class ClientCtx:
        async def __aenter__(self):
            return client

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kwargs: ClientCtx(),
    )

    service = EmbeddingService(redis_client=None)

    with pytest.raises(ValueError):
        await service.embed_text("hello")


@pytest.mark.asyncio
async def test_embed_text_success(monkeypatch):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "embeddings": [
            [1.0, 2.0, 3.0],
        ]
    }

    client = AsyncMock()
    client.post.return_value = response

    class ClientCtx:
        async def __aenter__(self):
            return client

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(
        "httpx.AsyncClient",
        lambda **kwargs: ClientCtx(),
    )

    service = EmbeddingService(redis_client=None)

    result = await service.embed_text("hello")

    assert result == [1.0, 2.0, 3.0]
    client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_embed_in_batches_multiple_batches(monkeypatch):
    service = EmbeddingService(None)

    monkeypatch.setattr(
        "app.rag.embeddings.OPENAI_EMBEDDING_BATCH_SIZE",
        2,
    )

    monkeypatch.setattr(
        service,
        "_call_ollama_embedding",
        AsyncMock(
            side_effect=[
                [[1.0], [2.0]],
                [[3.0]],
            ]
        ),
    )

    result = await service._embed_in_batches(
        ["a", "b", "c"],
    )

    assert result == [
        [1.0],
        [2.0],
        [3.0],
    ]

    assert service._call_ollama_embedding.await_count == 2


@pytest.mark.asyncio
async def test_embed_in_batches_single_batch(monkeypatch):
    service = EmbeddingService(None)

    monkeypatch.setattr(
        "app.rag.embeddings.OPENAI_EMBEDDING_BATCH_SIZE",
        100,
    )

    monkeypatch.setattr(
        service,
        "_call_ollama_embedding",
        AsyncMock(
            return_value=[
                [1.0],
                [2.0],
            ]
        ),
    )

    result = await service._embed_in_batches(
        ["a", "b"],
    )

    assert result == [
        [1.0],
        [2.0],
    ]

    service._call_ollama_embedding.assert_awaited_once()


@pytest.mark.asyncio
async def test_embed_batch_partial_cache(monkeypatch):
    redis = AsyncMock()

    service = EmbeddingService(redis)

    monkeypatch.setattr(
        service,
        "_get_cached_embedding",
        AsyncMock(
            side_effect=[
                [1.0],
                None,
                None,
            ]
        ),
    )

    monkeypatch.setattr(
        service,
        "_embed_in_batches",
        AsyncMock(
            return_value=[
                [2.0],
                [3.0],
            ]
        ),
    )

    monkeypatch.setattr(
        service,
        "_cache_embedding",
        AsyncMock(),
    )

    result = await service.embed_batch(
        ["a", "b", "c"],
    )

    assert result == [
        [1.0],
        [2.0],
        [3.0],
    ]

    service._embed_in_batches.assert_awaited_once_with(
        ["b", "c"],
    )

    assert service._cache_embedding.await_count == 2


@pytest.mark.asyncio
async def test_embed_batch_all_cached(monkeypatch):
    redis = AsyncMock()

    service = EmbeddingService(redis)

    monkeypatch.setattr(
        service,
        "_get_cached_embedding",
        AsyncMock(
            side_effect=[
                [1.0],
                [2.0],
            ]
        ),
    )

    monkeypatch.setattr(
        service,
        "_embed_in_batches",
        AsyncMock(),
    )

    result = await service.embed_batch(["a", "b"])

    assert result == [[1.0], [2.0]]
    service._embed_in_batches.assert_not_called()


@pytest.mark.asyncio
async def test_embed_batch_without_cache(monkeypatch):
    service = EmbeddingService(redis_client=None)

    monkeypatch.setattr(
        service,
        "_embed_in_batches",
        AsyncMock(return_value=[[1.0], [2.0]]),
    )

    result = await service.embed_batch(["a", "b"])

    assert result == [[1.0], [2.0]]
    service._embed_in_batches.assert_awaited_once_with(["a", "b"])


@pytest.mark.asyncio
async def test_embed_batch_empty():
    service = EmbeddingService(redis_client=None)

    result = await service.embed_batch([])

    assert result == []


@pytest.mark.asyncio
async def test_cache_embedding_success():
    redis = AsyncMock()

    service = EmbeddingService(redis)

    await service._cache_embedding("abc", [1.0, 2.0])

    redis.setex.assert_awaited_once()

    _, _, value = redis.setex.await_args.args

    assert json.loads(value) == [1.0, 2.0]


@pytest.mark.asyncio
async def test_get_cached_embedding_miss():
    redis = AsyncMock()
    redis.get.return_value = None

    service = EmbeddingService(redis)

    result = await service._get_cached_embedding("abc")

    assert result is None


@pytest.mark.asyncio
async def test_get_cached_embedding_hit():
    redis = AsyncMock()
    redis.get.return_value = json.dumps([1.0, 2.0])

    service = EmbeddingService(redis)

    result = await service._get_cached_embedding("abc")

    assert result == [1.0, 2.0]


@pytest.mark.asyncio
async def test_cache_embedding_no_redis():
    service = EmbeddingService(redis_client=None)

    await service._cache_embedding("abc", [1.0, 2.0])


@pytest.mark.asyncio
async def test_get_cached_embedding_no_redis():
    service = EmbeddingService(redis_client=None)

    result = await service._get_cached_embedding("abc")

    assert result is None


def test_cache_key_has_prefix():
    service = EmbeddingService(redis_client=None)

    key = service._cache_key("abc")

    assert key.startswith("embedding:")


def test_cache_key_changes_for_different_text():
    service = EmbeddingService(redis_client=None)

    key1 = service._cache_key("hello")
    key2 = service._cache_key("world")

    assert key1 != key2


def test_cache_key_is_deterministic():
    service = EmbeddingService(redis_client=None)

    key1 = service._cache_key("hello")
    key2 = service._cache_key("hello")

    assert key1 == key2
