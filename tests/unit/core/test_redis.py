from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.memory.redis_memory import RedisMemoryStore
import json
import pytest
from unittest.mock import AsyncMock


def test_messages_key():
    assert RedisMemoryStore._messages_key("123") == "session:123:messages"


def test_summary_key():
    assert RedisMemoryStore._summary_key("123") == "session:123:summary"


def test_metadata_key():
    assert RedisMemoryStore._metadata_key("123") == "session:123:metadata"


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
async def test_set_summary():
    redis = AsyncMock()

    store = RedisMemoryStore(redis)

    await store.set_summary("s1", "summary")

    redis.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_summary():
    redis = AsyncMock()
    redis.get.return_value = "summary"

    store = RedisMemoryStore(redis)

    result = await store.get_summary("s1")

    assert result == "summary"


@pytest.mark.asyncio
async def test_set_metadata():
    redis = AsyncMock()

    store = RedisMemoryStore(redis)

    await store.set_metadata("s1", {"a": 1})

    redis.setex.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_metadata_empty():
    redis = AsyncMock()
    redis.get.return_value = None

    store = RedisMemoryStore(redis)

    result = await store.get_metadata("s1")

    assert result == {}


@pytest.mark.asyncio
async def test_get_metadata_success():
    redis = AsyncMock()
    redis.get.return_value = json.dumps({"user": "vitaliy"})

    store = RedisMemoryStore(redis)

    result = await store.get_metadata("s1")

    assert result == {"user": "vitaliy"}


# def test_messages_key():
#     assert (
#         RedisMemoryStore._messages_key("abc")
#         == "session:abc:messages"
#     )
#
# def test_summary_key():
#     assert (
#         RedisMemoryStore._summary_key("abc")
#         == "session:abc:summary"
#     )


def test_deserialize_human():
    msg = RedisMemoryStore._deserialize_message(
        {
            "type": "human",
            "content": "hello",
        }
    )

    assert isinstance(msg, HumanMessage)
    assert msg.content == "hello"


def test_deserialize_ai():
    msg = RedisMemoryStore._deserialize_message(
        {
            "type": "ai",
            "content": "answer",
        }
    )

    assert isinstance(msg, AIMessage)
    assert msg.content == "answer"


def test_deserialize_system():
    msg = RedisMemoryStore._deserialize_message(
        {
            "type": "system",
            "content": "rules",
        }
    )

    assert isinstance(msg, SystemMessage)
    assert msg.content == "rules"


def test_deserialize_unknown_defaults_to_human():
    msg = RedisMemoryStore._deserialize_message(
        {
            "type": "unknown",
            "content": "text",
        }
    )

    assert isinstance(msg, HumanMessage)
    assert msg.content == "text"


def test_deserialize_without_type():
    msg = RedisMemoryStore._deserialize_message(
        {
            "content": "hello",
        }
    )

    assert isinstance(msg, HumanMessage)
    assert msg.content == "hello"
