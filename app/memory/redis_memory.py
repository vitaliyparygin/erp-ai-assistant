"""
Conversational memory backed by Redis.
Stores message history per session with automatic TTL and summarization support.
"""
import json
from typing import Any

import redis.asyncio as aioredis
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

MESSAGE_TYPE_MAP = {
    "human": HumanMessage,
    "ai": AIMessage,
    "system": SystemMessage,
}


class RedisMemoryStore:
    """
    Redis-backed session memory with per-session TTL.

    Key schema:
      session:{session_id}:messages  → JSON list of serialized messages
      session:{session_id}:summary   → plain text summary
      session:{session_id}:metadata  → JSON metadata dict
    """

    def __init__(self, redis_client: aioredis.Redis) -> None:  # type: ignore[type-arg]
        self._redis = redis_client
        self._settings = get_settings()

    # -------------------------------------------------------------------------
    # Message History
    # -------------------------------------------------------------------------

    async def get_history(self, session_id: str) -> list[BaseMessage]:
        """Retrieve message history for a session."""
        key = self._messages_key(session_id)
        try:
            raw = await self._redis.get(key)
            if not raw:
                return []
            messages_data = json.loads(raw)
            return [self._deserialize_message(m) for m in messages_data]
        except Exception as e:
            logger.error("memory_get_history_error", session_id=session_id, error=str(e))
            return []

    async def add_user_message(self, session_id: str, content: str) -> None:
        """Append a user message to the session history."""
        await self._append_message(
            session_id,
            {"type": "human", "content": content},
        )

    async def add_ai_message(
        self,
        session_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append an AI response to the session history."""
        await self._append_message(
            session_id,
            {"type": "ai", "content": content, "metadata": metadata or {}},
        )

    async def _append_message(self, session_id: str, message: dict) -> None:
        """Atomically append a message and refresh the TTL."""
        key = self._messages_key(session_id)
        try:
            raw = await self._redis.get(key)
            messages = json.loads(raw) if raw else []
            messages.append(message)

            # Trim to max history to prevent unbounded growth
            max_msgs = self._settings.max_conversation_history
            if len(messages) > max_msgs:
                messages = messages[-max_msgs:]

            await self._redis.setex(
                key,
                self._settings.redis_session_ttl,
                json.dumps(messages),
            )
        except Exception as e:
            logger.error("memory_append_error", session_id=session_id, error=str(e))

    async def clear_history(self, session_id: str) -> None:
        """Delete a session's message history."""
        await self._redis.delete(self._messages_key(session_id))

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    async def get_summary(self, session_id: str) -> str | None:
        """Retrieve the conversation summary if it exists."""
        key = self._summary_key(session_id)
        return await self._redis.get(key)

    async def set_summary(self, session_id: str, summary: str) -> None:
        """Store a conversation summary."""
        key = self._summary_key(session_id)
        await self._redis.setex(key, self._settings.redis_session_ttl, summary)

    # -------------------------------------------------------------------------
    # Session Metadata
    # -------------------------------------------------------------------------

    async def get_metadata(self, session_id: str) -> dict[str, Any]:
        """Retrieve session metadata dict."""
        key = self._metadata_key(session_id)
        raw = await self._redis.get(key)
        return json.loads(raw) if raw else {}

    async def set_metadata(self, session_id: str, metadata: dict[str, Any]) -> None:
        """Store session metadata."""
        key = self._metadata_key(session_id)
        await self._redis.setex(
            key,
            self._settings.redis_session_ttl,
            json.dumps(metadata),
        )

    async def session_exists(self, session_id: str) -> bool:
        """Check whether the session is still active (not expired)."""
        return bool(await self._redis.exists(self._messages_key(session_id)))

    async def refresh_session_ttl(self, session_id: str) -> None:
        """Extend the session TTL on activity."""
        for key in [
            self._messages_key(session_id),
            self._summary_key(session_id),
            self._metadata_key(session_id),
        ]:
            await self._redis.expire(key, self._settings.redis_session_ttl)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _messages_key(session_id: str) -> str:
        return f"session:{session_id}:messages"

    @staticmethod
    def _summary_key(session_id: str) -> str:
        return f"session:{session_id}:summary"

    @staticmethod
    def _metadata_key(session_id: str) -> str:
        return f"session:{session_id}:metadata"

    @staticmethod
    def _deserialize_message(data: dict) -> BaseMessage:
        msg_type = data.get("type", "human")
        cls = MESSAGE_TYPE_MAP.get(msg_type, HumanMessage)
        return cls(content=data.get("content", ""))