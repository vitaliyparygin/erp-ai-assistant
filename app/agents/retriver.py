import json
import time
import re
from langgraph.graph import END, START, StateGraph
from tenacity import retry, stop_after_attempt, wait_exponential
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import Citation, RetrievedChunk
from langchain_ollama import ChatOllama
from app.rag.prompts import (
    QUERY_REWRITE_TEMPLATE,
    RETRIEVAL_ANALYSIS_TEMPLATE,
)
from app.rag.retriever import Reranker, VectorRetriever
import traceback

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

FIELD_PATTERNS = {
    "платник": "Customer:",
    "customer": "Customer:",
    "замовник": "Customer:",
    "contractor": "Contractor:",
    "виконавець": "Contractor:",
    "eic": "EIC:",
}
PROTECTED_TERMS = {
    "eic",
    "customer",
    "contractor",
    "executor",
    "stage",
    "status",
    "invoice",
    "agreement",
    "стадія",
    "угода",
}

def is_contract_query(query: str) -> bool:
    q = query.lower()

    keywords = [
        "договір",
        "контракт",
        "agreement",
        "contract",
        "договор"
    ]
    print("is_contract_query:",any(k in q for k in keywords))
    return any(k in q for k in keywords)


def has_contract_identifier(query: str) -> bool:
    return bool(
        re.search(
            r"[A-Z]{1,5}-\d{4}-\d+",
            query,
            re.IGNORECASE,
        )
    )
def is_ambiguous_contract_query(query: str) -> bool:
    if not isinstance(query, str):
        return False
    print(query)
    print('is_contract_query(query):',is_contract_query(query))
    print('not has_contract_identifier(query):', not has_contract_identifier(query))
    return (
        is_contract_query(query)
        and not has_contract_identifier(query)
    )

def requires_contract_disambiguation(
    query: str,
    docs: list,
) -> bool:
    print('---requires_contract_disambiguation----')
    if not is_ambiguous_contract_query(query):
        return False
    logger.warning(
        "RETRIEVED_DOCS",
        docs=[
            {
                "doc": c.metadata.get("document_name"),
                "score": c.score,
            }
            for c in docs[:10]
        ]
    )
    contract_docs = [
        d
        for d in docs
        if d.metadata.get("document_type") == "contract"
    ]
    print('----len(contract_docs):', len(contract_docs))

    return len(contract_docs) > 1


def get_unique_docs(reranked: list) -> list:
    unique_docs = {}

    for chunk in reranked:
        unique_docs[chunk.document_name] = chunk

    return unique_docs

def build_contract_disambiguation(contracts):
    logger.debug(
        "build_contract_disambiguation:start"
    )

    logger.debug(
        "build_contract_disambiguation:len",
        len=len(contracts),
    )

    if not contracts:
        return None
    traceback.print_stack()
    lines = ["Я знайшов декілька договорів2:\n"]

    for idx, contract in enumerate(
        contracts,
        start=1,
    ):
        lines.append(
            f"{idx}. {contract['document_name']}"
        )

        if contract.get("contract_number"):
            lines.append(
                f"   Номер: {contract['contract_number']}"
            )

        if contract.get("valid_until"):
            lines.append(
                f"   Діє до: {contract['valid_until']}"
            )

        lines.append("")

    lines.append(
        "Уточніть, про який договір йде мова."
    )
    logger.debug(
        "build_contract_disambiguation:result",
        len=len(lines),
    )
    return "\n".join(lines)

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
        # RAG_RETRIEVAL_LATENCY = Histogram(
        #     "rag_retrieval_latency_ms",
        #     "Retrieval latency"
        # )
        #
        # RAG_RETRIEVED_CHUNKS = Histogram(
        #     "rag_retrieved_chunks_count",
        #     "Retrieved chunks count"
        # )

        logger.debug("retriever_agent_start", query=state.query[:60])
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

                latency = time.monotonic() - start_time
                logger.debug(
                    "REWRITTEN_QUERY2",
                    original=state.query,
                    rewritten=rewritten_query,
                    latency=latency
                )
            logger.warning(
                "FINAL_RETRIEVAL_QUERY",
                original=state.query,
                retrieval_query=rewritten_query,
            )
            start_time = time.monotonic()
            # 2. Semantic retrieval
            chunks = await self._retriever.retrieve(
                query=rewritten_query,
                document_ids=[str(d) for d in state.document_ids] or None,
            )
            logger.debug(
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
            logger.debug(
                "retrieved_chunks",
                count=len(chunks),
            )
            if chunks:
                logger.debug(
                    "first_chunk",
                    text=chunks[0].content[:300],
                )
            latency = time.monotonic() - start_time
            logger.debug(
                "self._retriever.retrieve:",
                count=latency,
            )
            # 3. Reranking
            start_time = time.monotonic()

            #dedub
            seen = set()
            unique_chunks = []
            for chunk in chunks:
                key = (
                    chunk.document_id,
                    chunk.chunk_index,
                )
                if key in seen:
                    continue
                seen.add(key)
                unique_chunks.append(chunk)
            chunks = unique_chunks

            reranked = await self._reranker.rerank(rewritten_query, chunks)
            unique_docs = get_unique_docs(chunks)
            logger.warning(
                "RETRIEVED_DOCS",
                docs=[
                    {
                        "doc": c.metadata.get("document_name"),
                        "score": c.score,
                    }
                    for c in reranked[:10]
            ])
            logger.warning(
                "UNIQUE_DOCS_AFTER_RERANK",
                docs=list(unique_docs.keys()),
            )
            if requires_contract_disambiguation(
                    state.query,
                    reranked,
            ):
                logger.warning(
                    "is_ambiguous_contract_query:true"
                )
                all_contracts = await self._retriever.get_contract_documents()
                logger.warning(
                    "CONTRACTS_FOUND",
                    count=len(all_contracts),
                    contracts=all_contracts,
                )
                unique = {}
                for contract in all_contracts:
                    key = (
                            contract.get("contract_number")
                            or contract.get("document_name")
                    )
                    unique[key] = contract

                contracts = list(unique.values())

                answer = build_contract_disambiguation(
                    contracts
                )
                logger.warning(
                    "is_ambiguous_contract_query:answer",
                    answer=answer
                )
                return {
                    "final_answer": answer,
                    "requires_clarification": True,
                    "agent_trace": {
                        "disambiguation": True,
                    },
                    "total_tokens": getattr(state.query, "usage_metadata", {}).get("total_tokens", 0),
                    "citations": [],
                }

            logger.debug(
                "RERANKED_CHUNKS",
                chunks=[
                    {
                        "doc": c.document_name,
                        "score": round(c.score, 3)
                    }
                    for c in reranked[:5]
                ]
            )
            logger.debug(
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
            logger.debug(
                "RERANKED_CHUNKS",latency=latency)

            # 4. Analyze context sufficiency
            start_time = time.monotonic()
            context_str = self._format_context(reranked[:2])
            latency = time.monotonic() - start_time
            logger.debug(
                "self._format_context:", latency=latency)
            start_time = time.monotonic()
            analysis = await self._analyze_context(state.query, context_str)
            latency = time.monotonic() - start_time

            logger.debug(
                "ANALYZE_CONTEXT_TIME:", latency=latency)
            analysis["has_sufficient_context"] = bool(reranked)
            analysis["needs_research"] = False

            latency_ms = round((time.monotonic() - start) * 1000, 2)

            logger.debug(
                "retriever_agent_done",
                retrieved=len(chunks),
                reranked=len(reranked),
                sufficient=analysis.get("has_sufficient_context", False),
                latency_ms=latency_ms,
            )
            logger.debug(
                "FINAL_CONTEXT",
                context=context_str,
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
        if any(
                term in state.query.lower()
                for term in PROTECTED_TERMS
        ):
            logger.debug(
                "QUERY_REWRITE_SKIPPED",
                query=state.query,
            )

            return state.query

        context = (
            "\n".join(
                f"{m.type}: {m.content[:200]}"
                for m in state.messages[-4:]
            )
            if state.messages
            else "No prior context"
        )

        chain = QUERY_REWRITE_TEMPLATE | self._llm
        logger.debug(
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