import time
from app.agents.state import AgentState
from app.core.logging import get_logger
from app.models.schemas import Citation
from langchain_ollama import ChatOllama
from app.rag.prompts import (
    SUMMARIZER_TEMPLATE,
)
from uuid import UUID
from app.config.constants import MAX_CONTEXT

logger = get_logger(__name__)


def build_citations(state: AgentState) -> list[Citation]:
    citations = []
    seen = set()

    for chunk in state.reranked_chunks[:3]:
        key = (
            chunk.document_id,
            chunk.page_number,
            chunk.chunk_index,
        )

        if key in seen:
            continue

        seen.add(key)

        citations.append(
            Citation(
                document_id=UUID(chunk.document_id),
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                chunk_content=chunk.content[:300],
                relevance_score=chunk.score,
                chunk_index=chunk.chunk_index,
            )
        )

    return citations


class SummarizerAgent:
    """
    Generates the final business-friendly answer with Markdown formatting.
    """

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

        logger.warning("LLM_MODEL", model=getattr(self._llm, "model", "unknown"))

    def _build_chain(self):
        return SUMMARIZER_TEMPLATE | self._llm

    async def __call__(self, state: AgentState) -> dict:
        start = time.monotonic()
        logger.debug("summarizer_agent_start", query=state.query[:60])
        logger.debug("SUMMARIZER_STATE_KEYS", keys=list(state.model_dump().keys()))
        logger.debug("SUMMARIZER_RERANKED", count=len(state.reranked_chunks or []))

        logger.debug(
            "SUMMARIZER_RERANKED_DOCS",
            docs=[
                {
                    "doc": c.document_name,
                    "score": c.score,
                }
                for c in state.reranked_chunks
            ],
        )

        logger.debug(
            "SUMMARIZER_CONTEXT_FULL",
            context=state.context_str,
        )

        logger.debug(
            "SUMMARIZER_QUERY",
            query=state.query,
        )
        try:
            # ambiguity_answer = build_disambiguation_answer(
            #     query=state.query,
            #     chunks=state.retrieved_chunks,
            # )
            #
            # if ambiguity_answer:
            #     state.final_answer = ambiguity_answer
            #     return state

            logger.debug(
                "summarizer_context",
                context_len=len(state.context_str),
                preview=state.context_str[:500],
            )
            chain = self._build_chain()

            logger.debug(
                "SUMMARIZER_INPUT",
                query=state.query,
                context=state.context_str[:2000],
                hustory=state.messages[-6:],
                research_notes="\n".join(state.research_notes),
            )
            logger.debug(
                "HISTORY_DEBUG",
                count=len(state.messages),
                data=str(state.messages[-6:])[:3000],
            )
            result = await chain.ainvoke(
                {
                    "query": (state.rewritten_query or state.query),
                    "context": state.context_str[:MAX_CONTEXT],
                    "history": state.messages[-6:],
                    "research_notes": "\n".join(state.research_notes),
                }
            )

            answer = result.content
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.debug(
                "OLLAMA_RESPONSE",
                seconds=latency_ms,
                answer_len=len(result.content),
            )
            logger.debug(
                "CONTEXT_STATS",
                context_len=len(state.context_str),
                history_len=len(state.messages),
                research_len=len("\n".join(state.research_notes)),
            )
            logger.debug(
                "summarizer_agent_done",
                answer_len=len(answer),
                latency_ms=latency_ms,
            )
            logger.debug("AGENT_TIMING", agent="summarier", latency_ms=latency_ms)
            logger.debug(
                "SUMMARIZER_MODEL",
                model=self._llm.__class__.__name__,
            )
            return {
                "final_answer": answer,
                "citations": build_citations(state),
                "intermediate_answers": [answer],
                "execution_path": ["summarizer"],
                "agent_trace": {
                    "summarizer": {
                        "answer_length": len(answer),
                        "latency_ms": latency_ms,
                    }
                },
                "total_tokens": getattr(result, "usage_metadata", {}).get(
                    "total_tokens", 0
                ),
            }

        except Exception as e:
            logger.error(
                "SUMMARIZER_FAILED",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
