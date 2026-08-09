"""
LangGraph multi-agent orchestration graph.
Implements: Retriever → Research → Summarizer → Citation → Memory pipeline
with conditional routing, retry handling, and full observability.
"""

import time
from typing import Any, Literal
from langgraph.graph import END, START, StateGraph
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.logging import get_logger
from langchain_ollama import ChatOllama

from app.rag.retriever.vector_retriever import VectorRetriever
from app.rag.retriever.reranker import Reranker

from app.agents.retriever import RetrieverAgent
from app.agents.memory import MemoryAgent
from app.agents.research import ResearchAgent
from app.agents.summarize import SummarizerAgent
from app.agents.citation import CitationAgent
from app.utils.resources import load_json
from app.observability.metrics import GRAPH_EXECUTIONS_TOTAL, GRAPH_LATENCY_SECONDS
from app.observability.llm import InstrumentedLLM

logger = get_logger(__name__)

REWRITE_MAP = load_json("rewrite_map.json")
FIELD_PATTERNS = load_json("field_patterns.json")
PROTECTED_TERMS = load_json("protected_terms.json")


# =============================================================================
# Graph Builder
# =============================================================================
def should_summarize(
    state: AgentState,
):
    return not state.disambiguated


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
        llm=None,
    ) -> None:
        settings = get_settings()
        logger.debug(
            "ACTIVE_SETTINGS",
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )
        self._llm = llm or ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
            num_predict=settings.ollama_num_predict,
        )

        retriever_llm = InstrumentedLLM(
            self._llm,
            model=settings.ollama_model,
            agent="retriever",
        )

        memory_llm = InstrumentedLLM(
            self._llm,
            model=settings.ollama_model,
            agent="memory",
        )

        research_llm = InstrumentedLLM(
            self._llm,
            model=settings.ollama_model,
            agent="research",
        )

        summarizer_llm = InstrumentedLLM(
            self._llm,
            model=settings.ollama_model,
            agent="summarizer",
        )

        citation_llm = InstrumentedLLM(
            self._llm,
            model=settings.ollama_model,
            agent="citation",
        )

        self._memory_agent = MemoryAgent(
            llm=memory_llm,
            memory_store=memory_store,
        )

        self._citation_agent = CitationAgent(citation_llm)
        self._retriever_agent = RetrieverAgent(
            retriever_llm,
            retriever,
            reranker,
        )
        self._research_agent = ResearchAgent(
            llm=research_llm,
        )
        self._summarizer_agent = SummarizerAgent(
            llm=summarizer_llm,
        )

        self._graph = self._build_graph()

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

        builder.add_conditional_edges(
            "retriever",
            self._route_after_retrieval,
            {
                "research": "research",
                "summarizer": "summarizer",
                "end": END,
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

        initial_state = AgentState(
            session_id=session_id or "",
            query=message,
            original_query=message,
            retrieved_chunks=[],
            citations=[],
            final_answer=None,
        )

        result = await self._graph.ainvoke(initial_state)

        return result

    @staticmethod
    def _route_after_retrieval(
        state: AgentState,
    ) -> Literal["research", "summarizer", "end"]:
        logger.debug(
            "ROUTER_RESULT",
            state=state,
            needs_research=state.needs_research,
            has_sufficient_context=state.has_sufficient_context,
        )
        logger.debug(
            "ROUTER_DEBUG",
            requires_clarification=state.requires_clarification,
            final_answer=state.final_answer,
        )
        if state.requires_clarification:
            logger.debug("ROUTER_RETURN_END")
            return "end"

        if state.needs_research:
            return "research"

        return "summarizer"

    async def run(self, state: AgentState) -> AgentState:
        """Execute the full agent graph for a query."""
        start = time.perf_counter()
        logger.debug(
            "graph_execution_start",
            session_id=state.session_id,
            query=state.query[:60],
        )
        try:
            result = await self._graph.ainvoke(state)
            GRAPH_EXECUTIONS_TOTAL.labels(
                status="success",
            ).inc()
            logger.debug(
                "GRAPH_RESULT",
                result_type=type(result).__name__,
            )
            logger.debug(
                "GRAPH_RESULT_DEBUG",
                type=type(result).__name__,
                keys=list(result.keys()) if isinstance(result, dict) else None,
            )
            return AgentState(**result)

        except Exception:
            GRAPH_EXECUTIONS_TOTAL.labels(
                status="error",
            ).inc()
            raise

        finally:
            GRAPH_LATENCY_SECONDS.observe(time.perf_counter() - start)

    async def stream(self, state: AgentState):
        start = time.perf_counter()

        try:
            async for event in self._graph.astream_events(
                state,
                version="v2",
            ):
                yield event

            GRAPH_EXECUTIONS_TOTAL.labels(
                status="success",
            ).inc()

        except Exception:
            GRAPH_EXECUTIONS_TOTAL.labels(
                status="error",
            ).inc()
            raise

        finally:
            GRAPH_LATENCY_SECONDS.observe(time.perf_counter() - start)

    def build_graph(self) -> Any:
        return self._graph
