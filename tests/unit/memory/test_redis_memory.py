import pytest
from unittest.mock import AsyncMock
import json
from app.memory.redis_memory import RedisMemoryStore
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage


@pytest.mark.asyncio
async def test_append_message_trims_history(monkeypatch):
    redis = AsyncMock()

    existing = [
        {"type": "human", "content": "1"},
        {"type": "human", "content": "2"},
        {"type": "human", "content": "3"},
    ]

    redis.get.return_value = json.dumps(existing)

    store = RedisMemoryStore(redis)

    monkeypatch.setattr(
        store._settings,
        "max_conversation_history",
        3,
    )

    await store.add_user_message(
        "session1",
        "4",
    )

    _, _, raw = redis.setex.await_args.args

    messages = json.loads(raw)

    assert len(messages) == 3

    assert [m["content"] for m in messages] == [
        "2",
        "3",
        "4",
    ]


@pytest.mark.asyncio
async def test_get_history_multiple_message_types():
    redis = AsyncMock()

    redis.get.return_value = json.dumps(
        [
            {
                "type": "system",
                "content": "sys",
            },
            {
                "type": "human",
                "content": "hello",
            },
            {
                "type": "ai",
                "content": "answer",
            },
        ]
    )

    store = RedisMemoryStore(redis)

    history = await store.get_history("session1")

    assert isinstance(history[0], SystemMessage)
    assert isinstance(history[1], HumanMessage)
    assert isinstance(history[2], AIMessage)

    assert history[0].content == "sys"
    assert history[1].content == "hello"
    assert history[2].content == "answer"


@pytest.mark.asyncio
async def test_add_ai_message_with_metadata():
    redis = AsyncMock()
    redis.get.return_value = None

    store = RedisMemoryStore(redis)

    await store.add_ai_message(
        "session1",
        "answer",
        {
            "sources": ["doc1"],
            "score": 0.9,
        },
    )

    _, _, raw = redis.setex.await_args.args

    messages = json.loads(raw)

    assert len(messages) == 1

    assert messages[0]["type"] == "ai"
    assert messages[0]["content"] == "answer"

    assert messages[0]["metadata"] == {
        "sources": ["doc1"],
        "score": 0.9,
    }


@pytest.mark.asyncio
async def test_get_metadata():
    redis = AsyncMock()

    redis.get.return_value = json.dumps(
        {
            "user": "john",
            "lang": "en",
        }
    )

    store = RedisMemoryStore(redis)

    metadata = await store.get_metadata("session1")

    assert metadata == {
        "user": "john",
        "lang": "en",
    }


@pytest.mark.asyncio
async def test_set_metadata():
    redis = AsyncMock()

    store = RedisMemoryStore(redis)

    await store.set_metadata(
        "session1",
        {
            "user": "john",
            "lang": "en",
        },
    )

    redis.setex.assert_awaited_once()

    key, ttl, value = redis.setex.await_args.args

    assert key == "session:session1:metadata"
    assert ttl == store._settings.redis_session_ttl

    assert json.loads(value) == {
        "user": "john",
        "lang": "en",
    }


def test_key_helpers():
    assert RedisMemoryStore._messages_key("x") == "session:x:messages"
    assert RedisMemoryStore._summary_key("x") == "session:x:summary"
    assert RedisMemoryStore._metadata_key("x") == "session:x:metadata"


@pytest.mark.asyncio
async def test_get_history_invalid_json():
    redis = AsyncMock()
    redis.get.return_value = "not-json"

    store = RedisMemoryStore(redis)

    result = await store.get_history("s1")

    assert result == []


@pytest.mark.asyncio
async def test_append_message_redis_failure():
    redis = AsyncMock()
    redis.get.side_effect = Exception("boom")

    store = RedisMemoryStore(redis)

    await store.add_user_message("s1", "hello")

    redis.setex.assert_not_called()


@pytest.mark.asyncio
async def test_session_exists_true():
    redis = AsyncMock()
    redis.exists.return_value = 1

    store = RedisMemoryStore(redis)

    assert await store.session_exists("s1") is True


@pytest.mark.asyncio
async def test_session_exists_false():
    redis = AsyncMock()
    redis.exists.return_value = 0

    store = RedisMemoryStore(redis)

    assert await store.session_exists("s1") is False


@pytest.mark.asyncio
async def test_refresh_session_ttl():
    redis = AsyncMock()

    store = RedisMemoryStore(redis)

    await store.refresh_session_ttl("abc")

    assert redis.expire.await_count == 3


@pytest.mark.asyncio
async def test_clear_history():
    redis = AsyncMock()
    store = RedisMemoryStore(redis)

    await store.clear_history("s1")

    redis.delete.assert_awaited_once_with("session:s1:messages")


@pytest.mark.asyncio
async def test_get_summary_none():
    redis = AsyncMock()
    redis.get.return_value = None

    store = RedisMemoryStore(redis)

    assert await store.get_summary("s1") is None


@pytest.mark.asyncio
async def test_set_summary():
    redis = AsyncMock()

    store = RedisMemoryStore(redis)

    await store.set_summary("s1", "summary")

    redis.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_metadata_empty():
    redis = AsyncMock()
    redis.get.return_value = None

    store = RedisMemoryStore(redis)

    assert await store.get_metadata("s1") == {}
