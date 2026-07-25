from typing import Any
from app.rag.prompts import (
    CONVERSATION_SUMMARY_TEMPLATE,
)
from app.core.config import get_settings
from app.agents.state import AgentState
from app.core.logging import get_logger
import time

logger = get_logger(__name__)

class MemoryAgent:
    """
    Manages conversational context.
    Loads session history, summarizes long conversations.
    """

    def __init__(self, llm: Any, memory_store: Any) -> None:
        self._llm = llm
        self._memory = memory_store
        self._settings = get_settings()

    async def __call__(self, state: AgentState) -> dict:
        start = time.monotonic()
        logger.info("memory_agent_start", session_id=state.session_id)

        try:
            start_time = time.monotonic()
            history = await self._memory.get_history(state.session_id)
            logger.debug(
                "MEMORY_HISTORY",
                count=len(history),
                history=[
                    {
                        "type": type(m).__name__,
                        "content": str(m.content)[:100],
                    }
                    for m in history
                ]
            )
            logger.debug(
                "MEMORY_DEBUG",
                session_id=str(state.session_id),
                count=len(history),
                message_types=[
                    type(m).__name__
                    for m in history
                ]
            )
            logger.debug(
                "MEMORY_LAST_MESSAGES",
                messages=[
                    {
                        "type": type(m).__name__,
                        "content": str(m.content)[:100]
                    }
                    for m in history[-4:]
                ]
            )
            latency = time.monotonic() - start_time
            logger.debug("_memory.get_history:", latency=latency)
            message_count = len(history)
            logger.debug(
                "FINAL_CONTEXT",
                context=history[-4:]
            )

            logger.debug(
                "FINAL_QUERY",
                query=state.query
            )
            summary = None
            if message_count >= self._settings.memory_summarization_threshold:
                start = time.monotonic()
                # Summarize to keep context window manageable

                summary = await self._summarize_history(history)
                latency = time.monotonic() - start_time
                logger.debug("_memory._summarize_history:", latency=latency)
                # Keep only the last few messages after summarization
                history = history[-4:]

            updates: dict[str, Any] = {
                "messages": history,
                "message_count": message_count,
                "execution_path": ["memory"],
            }
            if summary:
                updates["conversation_summary"] = summary

            logger.debug(
                "memory_agent_done",
                session_id=state.session_id,
                history_len=message_count,
                summarized=summary is not None,
                latency_ms=round((time.monotonic() - start) * 1000, 2),
            )
            logger.debug(
                "AGENT_TIMING",
                agent="memory",
                latency_ms=round((time.monotonic() - start) * 1000, 2),
            )
            return updates

        except Exception as e:
            logger.error("memory_agent_error", error=str(e))
            return {"errors": [f"MemoryAgent: {e}"], "execution_path": ["memory"]}

    async def _summarize_history(self, history: list) -> str:
        """Use LLM to summarize a long conversation."""
        conversation_text = "\n".join(
            f"{msg.type.upper()}: {msg.content}" for msg in history
        )
        chain = CONVERSATION_SUMMARY_TEMPLATE | self._llm
        logger.debug(
            "SUMMARIZER_PROMPT",
            context=conversation_text[:2000]
        )

        result = await chain.ainvoke({"conversation": conversation_text})
        return result.content
