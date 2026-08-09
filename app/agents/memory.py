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

    def _build_summary_chain(self):
        return CONVERSATION_SUMMARY_TEMPLATE | self._llm

    async def __call__(self, state: AgentState) -> dict:
        start = time.perf_counter()
        logger.info("memory_agent_start", session_id=state.session_id)
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        try:
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
                ],
            )
            logger.debug(
                "MEMORY_DEBUG",
                session_id=str(state.session_id),
                count=len(history),
                message_types=[type(m).__name__ for m in history],
            )
            logger.debug(
                "MEMORY_LAST_MESSAGES",
                messages=[
                    {"type": type(m).__name__, "content": str(m.content)[:100]}
                    for m in history[-4:]
                ],
            )
            latency = time.monotonic() - start
            logger.debug("_memory.get_history:", latency=latency)
            message_count = len(history)
            logger.debug("FINAL_CONTEXT", context=history[-4:])

            logger.debug("FINAL_QUERY", query=state.query)
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0
            summary_result = None
            if message_count >= self._settings.memory_summarization_threshold:
                start_summary = time.monotonic()
                # Summarize to keep context window manageable

                summary_result, usage = await self._summarize_history(history)
                latency = time.monotonic() - start_summary
                logger.debug("_memory._summarize_history:", latency=latency)
                # Keep only the last few messages after summarization

                input_tokens = usage["input_tokens"]
                output_tokens = usage["output_tokens"]
                total_tokens = usage["total_tokens"]
                history = history[-4:]

            updates: dict[str, Any] = {
                "messages": history,
                "message_count": message_count,
                "execution_path": ["memory"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }
            if summary_result:
                updates["conversation_summary"] = summary_result

            logger.debug(
                "memory_agent_done",
                session_id=state.session_id,
                history_len=message_count,
                summarized=summary_result is not None,
                latency_ms=round((time.monotonic() - start) * 1000, 2),
            )
            logger.debug(
                "AGENT_TIMING",
                agent="memory",
                latency_ms=round((time.monotonic() - start) * 1000, 2),
            )

            return updates

        except Exception as e:
            logger.error(
                "memory_agent_error",
                error=str(e),
            )
            raise

    async def _summarize_history(self, history: list) -> tuple[str, dict[str, int]]:
        conversation_text = "\n".join(
            f"{msg.type.upper()}: {msg.content}" for msg in history
        )

        chain = self._build_summary_chain()

        result = await chain.ainvoke(
            {"conversation": conversation_text}
        )

        logger.debug(
            "MEMORY_SUMMARY_RESULT_DEBUG",
            result_type=type(result).__name__,
            result=str(result)[:2000],
        )

        usage = getattr(result, "usage_metadata", {}) or {}

        return (
            result.content,
            {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )
