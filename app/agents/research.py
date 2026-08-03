from app.rag.prompts import (
    RESEARCH_TEMPLATE,
)
from app.agents.state import AgentState
from app.core.logging import get_logger
import time
from langchain_ollama import ChatOllama

logger = get_logger(__name__)


class ResearchAgent:
    """
    Analyzes retrieved context and synthesizes intermediate insights.
    Activated only when the retriever flags insufficient context.
    """

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    def _build_chain(self):
        return RESEARCH_TEMPLATE | self._llm

    async def __call__(self, state: AgentState) -> dict:
        start = time.monotonic()
        logger.debug("research_agent_start", query=state.query[:60])

        try:
            chain = self._build_chain()

            result = await chain.ainvoke(
                {
                    "query": state.query,
                    "context": state.context_str,
                    "history": state.messages[-6:],
                    "research_notes": "\n".join(state.research_notes),
                }
            )
            logger.debug(
                "ROUTER_DECISION",
                needs_research=state.needs_research,
                query=state.query,
            )
            latency_ms = round(
                (time.monotonic() - start) * 1000,
                2,
            )
            logger.debug(
                "AGENT_RESULT",
                agent="research_agent",
                result_preview=str(result.content)[:500],
                latency_ms=latency_ms,
            )
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.debug("AGENT_TIMING", agent="research_agent", latency_ms=latency_ms)
            return {
                "research_notes": [result.content],
                "execution_path": ["research"],
                "agent_trace": {"research": {"latency_ms": latency_ms}},
            }

        except Exception as e:
            logger.error(
                "research_agent_error",
                error=str(e),
            )
            raise
