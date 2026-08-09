import time

from app.agents.state import AgentState
from app.core.logging import get_logger
from app.observability.metrics import (
    AGENT_EXECUTIONS_TOTAL,
    AGENT_LATENCY_SECONDS,
)
from app.rag.prompts import RESEARCH_TEMPLATE
from langchain_core.runnables import Runnable

logger = get_logger(__name__)


class ResearchAgent:
    """
    Analyzes retrieved context and synthesizes intermediate insights.
    Activated only when the retriever flags insufficient context.
    """

    def __init__(self, llm: Runnable) -> None:
        self._llm = llm
        self._chain = RESEARCH_TEMPLATE | llm

    async def __call__(self, state: AgentState) -> dict:
        start = time.perf_counter()

        logger.debug(
            "research_start",
            query=state.query[:60],
        )

        context = state.context_str
        research_notes = "\n".join(state.research_notes)

        conversation_context = "\n".join(
            f"{message.type}: {message.content[:200]}"
            for message in state.messages[-4:]
        )[:3000]

        logger.debug(
            "research_input",
            query=state.query,
            needs_research=state.needs_research,
            context_chars=len(state.context_str),
            history_messages=len(state.messages),
            research_notes_chars=sum(
                len(note) for note in state.research_notes
            ),
        )

        try:
            result = await self._chain.ainvoke(
                {
                    "query": state.query,
                    "context": context,
                    "research_notes": research_notes,
                    "conversation_context": conversation_context,
                }
            )
            usage = getattr(result, "usage_metadata", {}) or {}
            latency_ms = round(
                (time.perf_counter() - start) * 1000,
                2,
            )

            AGENT_EXECUTIONS_TOTAL.labels(
                agent="research",
                status="success",
            ).inc()

            logger.debug(
                "AGENT_RESULT",
                agent="research",
                result_preview=str(result.content)[:500],
                latency_ms=latency_ms,
            )

            return {
                "research_notes": [result.content],
                "execution_path": ["research"],
                "agent_trace": {
                    "research": {
                        "latency_ms": latency_ms,
                    }
                },
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

        except Exception:
            AGENT_EXECUTIONS_TOTAL.labels(
                agent="research",
                status="error",
            ).inc()
            raise

        finally:
            AGENT_LATENCY_SECONDS.labels(
                agent="research",
            ).observe(time.perf_counter() - start)