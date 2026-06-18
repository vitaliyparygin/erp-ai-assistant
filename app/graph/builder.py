"""
LangGraph multi-agent orchestration graph.
Implements: Retriever → Research → Summarizer → Citation → Memory pipeline
with conditional routing, retry handling, and full observability.
"""
import json
import time
from typing import Any, Literal
from uuid import UUID
from langgraph.graph import END, START, StateGraph
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Any
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.exceptions import AgentError, AgentTimeoutError
from app.core.logging import get_logger
from app.models.schemas import Citation, RetrievedChunk
from app.observability.langfuse_client import LangFuseTracer
from langchain_ollama import ChatOllama
from app.rag.prompts import (
    CITATION_EXTRACTION_TEMPLATE,
    CONVERSATION_SUMMARY_TEMPLATE,
    QUERY_REWRITE_TEMPLATE,
    RESEARCH_TEMPLATE,
    RETRIEVAL_ANALYSIS_TEMPLATE,
    SUMMARIZER_TEMPLATE,
)
from app.rag.retriever import Reranker, VectorRetriever

logger = get_logger(__name__)

REWRITE_MAP = {
    "виконавець договору": [
        "contractor",
        "service provider",
        "executor",
    ],

    "замовник договору": [
        "customer",
        "client",
    ],

    "номер договору": [
        "contract number",
        "agreement number",
    ],

    "працівник": [
        "employee",
        "worker",
    ],

    "наказ": [
        "employee order",
        "order",
    ],
}
# =============================================================================
# Agent Nodes
# =============================================================================

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
            logger.warning(
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
            logger.warning(
                "MEMORY_DEBUG",
                session_id=str(state.session_id),
                count=len(history),
                message_types=[
                    type(m).__name__
                    for m in history
                ]
            )
            logger.warning(
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
            logger.info("_memory.get_history:", latency=latency)
            message_count = len(history)
            logger.warning(
                "FINAL_CONTEXT",
                context=history[-4:]
            )

            logger.warning(
                "FINAL_QUERY",
                query=state.query
            )
            summary = None
            if message_count >= self._settings.memory_summarization_threshold:
                start = time.monotonic()
                # Summarize to keep context window manageable

                summary = await self._summarize_history(history)
                latency = time.monotonic() - start_time
                logger.info("_memory._summarize_history:", latency=latency)
                # Keep only the last few messages after summarization
                history = history[-4:]

            updates: dict[str, Any] = {
                "messages": history,
                "message_count": message_count,
                "execution_path": ["memory"],
            }
            if summary:
                updates["conversation_summary"] = summary

            logger.info(
                "memory_agent_done",
                session_id=state.session_id,
                history_len=message_count,
                summarized=summary is not None,
                latency_ms=round((time.monotonic() - start) * 1000, 2),
            )
            logger.info(
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
        logger.warning(
            "SUMMARIZER_PROMPT",
            context=conversation_text[:2000]
        )

        result = await chain.ainvoke({"conversation": conversation_text})
        return result.content


class RetrieverAgent:
    """
    Semantic search agent.
    Rewrites the query, retrieves relevant chunks, and evaluates context sufficiency.
    """

    def __init__(
        self,
        llm: ChatOllama,
        retriever: VectorRetriever,
        reranker: Reranker,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._reranker = reranker
        self._settings = get_settings()

    async def __call__(self, state: AgentState) -> dict:
        logger.info("retriever_agent_start", query=state.query[:60])
        start = time.monotonic()
        try:
            # 1. Query rewriting
            rewritten_query = state.query.lower()

            for ua, synonyms in REWRITE_MAP.items():
                if ua in rewritten_query:
                    rewritten_query += " " + " ".join(synonyms)

            if self._settings.query_rewrite_enabled:
                start_time = time.monotonic()
                rewritten_query = await self._rewrite_query(state)
                logger.warning(
                    "REWRITTEN_QUERY2",
                    original=state.query,
                    rewritten=rewritten_query,
                )
                latency = time.monotonic() - start_time
                print("self._rewrite_query:", latency)

            start_time = time.monotonic()
            # 2. Semantic retrieval
            chunks = await self._retriever.retrieve(
                query=rewritten_query,
                document_ids=[str(d) for d in state.document_ids] or None,
            )
            logger.warning(
                "RETRIEVED_RAW",
                query=rewritten_query,
                docs=[
                    {
                        "doc": c.document_name,
                        "score": round(c.score, 3),
                        "chunk": c.chunk_index,
                    }
                    for c in chunks
                ],
            )
            logger.warning(
                "retrieved_chunks",
                count=len(chunks),
            )
            if chunks:
                logger.warning(
                    "first_chunk",
                    text=chunks[0].content[:300],
                )
            latency = time.monotonic() - start_time
            print("self._retriever.retrieve:", latency)
            # 3. Reranking
            start_time = time.monotonic()
            reranked = await self._reranker.rerank(rewritten_query, chunks)
            logger.warning(
                "RERANKED_CHUNKS",
                chunks=[
                    {
                        "doc": c.document_name,
                        "score": round(c.score, 3)
                    }
                    for c in reranked[:5]
                ]
            )
            logger.warning(
                "RERANK_OUTPUT",
                docs=[
                    {
                        "doc": c.document_name,
                        "score": round(c.score, 3),
                    }
                    for c in reranked
                ]
            )
            latency = time.monotonic() - start_time
            print("self._reranker.rerank:", latency)
            # 4. Analyze context sufficiency
            start_time = time.monotonic()
            context_str = self._format_context(reranked)
            latency = time.monotonic() - start_time
            print("self._format_context:", latency)
            start_time = time.monotonic()
            analysis = await self._analyze_context(state.query, context_str)
            latency = time.monotonic() - start_time
            print("ANALYZE_CONTEXT_TIME:", latency)
            analysis["has_sufficient_context"] = bool(reranked)
            analysis["needs_research"] = False

            latency_ms = round((time.monotonic() - start) * 1000, 2)

            logger.info(
                "retriever_agent_done",
                retrieved=len(chunks),
                reranked=len(reranked),
                sufficient=analysis.get("has_sufficient_context", False),
                latency_ms=latency_ms,
            )

            return {
                "rewritten_query": rewritten_query,
                "retrieved_chunks": chunks,
                "reranked_chunks": reranked,
                "context_str": context_str,
                "has_sufficient_context": analysis.get("has_sufficient_context", bool(reranked)),
                "needs_research": analysis.get("needs_research", False),
                "retrieval_latency_ms": latency_ms,
                "execution_path": ["retriever"],
                "agent_trace": {"retriever": {
                    "query": rewritten_query,
                    "chunks_retrieved": len(chunks),
                    "chunks_reranked": len(reranked),
                    "latency_ms": latency_ms,
                }},
            }

        except Exception as e:
            logger.error("retriever_agent_error", error=str(e))
            return {
                "errors": [f"RetrieverAgent: {e}"],
                "has_sufficient_context": False,
                "execution_path": ["retriever"],
            }

    async def _rewrite_query(self, state: AgentState) -> str:
        """Rewrite the query for better retrieval."""
        # logger.warning(
        #     "QUERY_REWRITE_DISABLED",
        #     query=state.query,
        # )
        #
        # return state.query
        context = (
            "\n".join(
                f"{m.type}: {m.content[:200]}"
                for m in state.messages[-4:]
            )
            if state.messages
            else "No prior context"
        )

        chain = QUERY_REWRITE_TEMPLATE | self._llm
        logger.warning(
            "QUERY_USED_FOR_SEARCH",
            query=state.query,
        )

        result = await chain.ainvoke({
            "query": state.query,
            "conversation_context": context[:3000],
        })

        rewritten = result.content.strip()

        logger.debug(
            "RETRIEVAL_QUERY",
            original=state.query,
            rewritten=rewritten,
        )

        return rewritten

    async def _analyze_context(self, query: str, context: str) -> dict:
        """Check if retrieved context is sufficient to answer the query."""
        if not context:
            return {"has_sufficient_context": False, "needs_research": False}

        chain = RETRIEVAL_ANALYSIS_TEMPLATE | self._llm
        result = await chain.ainvoke({"query": query, "context": context[:3000]})


        try:
            analysis = json.loads(result.content)
        except json.JSONDecodeError:
            analysis = {"has_sufficient_context": True, "needs_research": False}

        return analysis

    @staticmethod
    def _format_context(chunks: list[RetrievedChunk]) -> str:
        """Format chunks into a readable context string."""
        if not chunks:
            return ""

        parts = []
        for i, chunk in enumerate(chunks, 1):
            page_info = f" (page {chunk.page_number})" if chunk.page_number else ""
            parts.append(
                f"[Source {i}: {chunk.document_name}{page_info}, score={chunk.score:.3f}]\n"
                f"{chunk.content}"
            )
        return "\n\n---\n\n".join(parts)


class ResearchAgent:
    """
    Analyzes retrieved context and synthesizes intermediate insights.
    Activated only when the retriever flags insufficient context.
    """

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def __call__(self, state: AgentState) -> dict:
        start = time.monotonic()
        logger.info("research_agent_start", query=state.query[:60])

        try:
            chain = RESEARCH_TEMPLATE | self._llm

            result = await chain.ainvoke({
                "query": state.query,
                "context": state.context_str,
                "history": state.messages[-6:],
                "research_notes": "\n".join(state.research_notes),
            })
            logger.warning(
                "ROUTER_DECISION",
                needs_research=state.needs_research,
                query=state.query,
            )
            logger.info(
                "AGENT_result",
                agent="research_agent",
                latency_ms=result
            )
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.info(
                "AGENT_TIMING",
                agent="research_agent",
                latency_ms=latency_ms
            )
            return {
                "research_notes": [result.content],
                "execution_path": ["research"],
                "agent_trace": {"research": {"latency_ms": latency_ms}},
            }

        except Exception as e:
            logger.error("research_agent_error", error=str(e))
            return {"errors": [f"ResearchAgent: {e}"], "execution_path": ["research"]}


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

        logger.warning(
            "LLM_MODEL",
            model=getattr(self._llm, "model", "unknown")
        )


    async def __call__(self, state: AgentState) -> dict:
        start = time.monotonic()
        logger.info("summarizer_agent_start", query=state.query[:60])
        logger.warning(
            "SUMMARIZER_STATE_KEYS",
            keys=list(state.model_dump().keys())
        )
        logger.warning(
            "SUMMARIZER_RERANKED",
            count=len(state.reranked_chunks or [])
        )

        logger.warning(
            "SUMMARIZER_RERANKED_DOCS",
            docs=[
                {
                    "doc": c.document_name,
                    "score": c.score,
                }
                for c in state.reranked_chunks
            ],
        )

        logger.warning(
            "SUMMARIZER_CONTEXT_FULL",
            context=state.context_str,
        )

        logger.warning(
            "SUMMARIZER_QUERY",
            query=state.query,
        )
        try:
            logger.warning(
                "summarizer_context",
                context_len=len(state.context_str),
            )

            logger.warning(
                "summarizer_context_preview",
                preview=state.context_str[:500],
            )
            chain = SUMMARIZER_TEMPLATE | self._llm

            logger.warning(
                "SUMMARIZER_INPUT",
                query=state.query,
                context=state.context_str[:2000],
                hustory=state.messages[-6:],
                research_notes = "\n".join(state.research_notes)
            )
            logger.warning(
                "HISTORY_DEBUG",
                count=len(state.messages),
                data=str(state.messages[-6:])[:3000]
            )
            result = await chain.ainvoke({
                "query": state.query,
                "context": state.context_str[:2000],
                "history": state.messages[-6:],
                "research_notes": "\n".join(state.research_notes),
            })

            answer = result.content
            latency_ms = round((time.monotonic() - start) * 1000, 2)
            logger.warning(
                "OLLAMA_RESPONSE",
                seconds=latency_ms,
                answer_len=len(result.content),
            )
            logger.warning(
                "CONTEXT_STATS",
                context_len=len(state.context_str),
                history_len=len(state.messages),
                research_len=len("\n".join(state.research_notes)),
            )
            logger.info(
                "summarizer_agent_done",
                answer_len=len(answer),
                latency_ms=latency_ms,
            )
            logger.info(
                "AGENT_TIMING",
                agent="summarier",
                latency_ms=latency_ms
            )
            logger.warning(
                "SUMMARIZER_MODEL",
                model=self._llm.__class__.__name__,
            )
            return {
                "final_answer": answer,
                "citations": build_citations(
                    state
                ),
                "intermediate_answers": [answer],
                "execution_path": ["summarizer"],
                "agent_trace": {"summarizer": {
                    "answer_length": len(answer),
                    "latency_ms": latency_ms,
                }},
                "total_tokens": getattr(result, "usage_metadata", {}).get("total_tokens", 0),
            }


        except Exception as e:

            logger.error(
                "SUMMARIZER_FAILED",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise


class CitationAgent:
    """
    Extracts citations from the answer and maps them to source chunks.
    """

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def __call__(self, state: AgentState) -> dict:
        if not state.final_answer or not state.reranked_chunks:
            return {"citations": [], "execution_path": ["citation"]}

        start = time.monotonic()

        return {
            "citations": [
                Citation(
                    document_id=UUID(c.document_id),
                    document_name=c.document_name,
                    page_number=c.page_number,
                    chunk_content=c.content[:300],
                    relevance_score=c.score,
                    chunk_index=c.chunk_index,
                )
                for c in state.reranked_chunks[:3]
            ]
        }


# =============================================================================
# Graph Builder
# =============================================================================

class ERPAssistantGraph:
    """
    LangGraph orchestration graph for the ERP AI Assistant.

    Flow:
        memory → retriever → [research (conditional)] → summarizer → citation → END
    """

    def __init__(
        self,
        retriever: VectorRetriever,
        reranker: Reranker,
        memory_store: Any,
    ) -> None:
        settings = get_settings()
        logger.warning(
            "ACTIVE_SETTINGS",
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )
        self._llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
            request_timeout = settings.ollama_request_timeout,
        )


        self._memory_agent = MemoryAgent(self._llm, memory_store)
        self._retriever_agent = RetrieverAgent(self._llm, retriever, reranker)
        self._research_agent = ResearchAgent(self._llm)
        self._summarizer_agent = SummarizerAgent(self._llm)
        self._citation_agent = CitationAgent(self._llm)

        self._graph = self._build_graph()
        # result = await _graph.invoke(
        #     message=request.message,
        #     session_id=request.session_id,
        # )

    def _build_graph(self) -> Any:
        """Construct and compile the LangGraph state machine."""
        builder = StateGraph(AgentState)

        builder.add_node("memory", self._memory_agent)
        builder.add_node("retriever", self._retriever_agent)
        builder.add_node("research", self._research_agent)
        builder.add_node("summarizer", self._summarizer_agent)
        # builder.add_node("citation", self._citation_agent)

        builder.add_edge(START, "memory")
        builder.add_edge("memory", "retriever")
        # builder.add_edge("retriever", "research")
        builder.add_conditional_edges(
            "retriever",
            self._route_after_retrieval,
            {
                "research": "research",
                "summarizer": "summarizer",
            },
        )
        builder.add_edge("research", "summarizer")
        # builder.add_edge("summarizer", "citation")
        builder.add_edge("summarizer", END)

        return builder.compile()


    async def invoke(
            self,
            message: str,
            session_id: str | None = None,
    ) -> dict:
        """
        Execute the LangGraph pipeline.
        """

        initial_state = {
            "user_query": message,
            "session_id": session_id,
            "retrieved_chunks": [],
            "citations": [],
            "answer": "",
        }

        result = await self._graph.ainvoke(initial_state)

        return result

    @staticmethod
    def _route_after_retrieval(
        state: AgentState,
    ) -> Literal["research", "summarizer"]:
        logger.warning(
            "ROUTER_RESULT",
            state=state,
            needs_research=state.needs_research,
            has_sufficient_context=state.has_sufficient_context
        )
        """Route to research if context is insufficient, else go straight to summarizer."""
        if state.needs_research and not state.has_sufficient_context:
            return "research"
        return "summarizer"

    async def run(self, state: AgentState) -> AgentState:
        """Execute the full agent graph for a query."""
        logger.info(
            "graph_execution_start",
            session_id=state.session_id,
            query=state.query[:60],
        )
        try:
            result = await self._graph.ainvoke(state)

            logger.warning(
                "GRAPH_RESULT",
                result_type=type(result).__name__,
            )
            logger.warning(
                "GRAPH_RESULT_DEBUG",
                type=type(result).__name__,
                keys=list(result.keys()) if isinstance(result, dict) else None,
            )
            return AgentState(**result)

        except Exception as e:
            print("GRAPH FAILED")
            print(type(e))
            print(str(e))
            raise
        logger.info(
            "graph_execution_complete",
            session_id=state.session_id,
            path=result.get("execution_path", []),
            citations=len(result.get("citations", [])),
            has_answer=bool(result.get("final_answer")),
        )

        return AgentState(**result)

    async def stream(self, state: AgentState):
        """Stream graph execution events for real-time UI updates."""
        async for event in self._graph.astream_events(state, version="v2"):
            yield event