import json
import time
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import RetrievedChunk
from langchain_ollama import ChatOllama
from app.rag.prompts import (
    QUERY_REWRITE_TEMPLATE,
    RETRIEVAL_ANALYSIS_TEMPLATE,
)
from app.rag.retriever.vector_retriever import VectorRetriever
from app.rag.retriever.reranker import Reranker
from app.ingestion.query_metadata import extract_query_metadata
from app.utils.resources import load_json
from app.retrieval.contracts import (
    get_unique_docs,
    requires_contract_disambiguation,
    build_contract_disambiguation,
)
from app.rag.query_rewriter import QueryRewriter
from app.config.constants import MAX_CONTEXT
from app.rag.context.assembler import ContextAssembler

logger = get_logger(__name__)
# REWRITE_MAP = load_json("rewrite_map.json")
FIELD_PATTERNS = load_json("field_patterns.json")
# PROTECTED_TERMS = load_json("protected_terms.json")


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
            query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._reranker = reranker
        self._query_rewriter = query_rewriter or QueryRewriter(llm)
        self._settings = get_settings()
        self._context_assembler = ContextAssembler(
            max_context=MAX_CONTEXT,
        )
        self._query_rewriter = (
            query_rewriter
            or QueryRewriter(llm=llm)
        )
    def _build_rewrite_chain(self):
        return QUERY_REWRITE_TEMPLATE | self._llm

    async def __call__(self, state: AgentState) -> dict:

        logger.debug("retriever_agent_start", query=state.query[:60])
        start = time.monotonic()
        try:
            # 1. Query rewriting
            rewrite_start = time.monotonic()

            if self._settings.query_rewrite_enabled:
                rewritten_query = await self._rewrite_query(state)
            else:
                rewritten_query = state.query.strip().lower()

            rewrite_latency_ms = round(
                (time.monotonic() - rewrite_start) * 1000,
                2,
            )

            logger.debug(
                "query_rewrite_completed",
                original=state.query,
                rewritten=rewritten_query,
                latency_ms=rewrite_latency_ms,
                enabled=self._settings.query_rewrite_enabled,
            )

            latency = time.monotonic() - start
            logger.debug(
                "retrieval_query",
                original=state.query,
                rewritten=rewritten_query,
                latency=latency,
            )
            logger.debug(
                "low_retrieval_confidence",
                original=state.query,
                retrieval_query=rewritten_query,
            )
            start_time = time.monotonic()

            query_metadata = extract_query_metadata(rewritten_query)
            logger.debug(
                "query_metadata",
                query_metadata=query_metadata,
            )

            chunks = await self._retriever.retrieve(
                query=rewritten_query,
                document_ids=[str(d) for d in state.document_ids] or None,
                query_metadata=query_metadata,
            )
            logger.debug(
                "retrieval_raw",
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

            # dedub
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

            reranked = await self._reranker.rerank(
                query=rewritten_query,
                chunks=chunks,
            )
            unique_docs = get_unique_docs(chunks)
            logger.debug(
                "retrieval_docs",
                docs=[
                    {
                        "doc": chunk.document_name,
                        "score": c.score,
                    }
                    for c in reranked[:10]
                ],
            )
            logger.debug(
                "unique_docs_after_rerank",
                docs=list(unique_docs.keys()),
            )
            if requires_contract_disambiguation(
                state.query,
                reranked,
            ):
                logger.debug("is_ambiguous_contract_query:true")
                all_contracts = await self._retriever.get_contract_documents()
                logger.debug(
                    "contract_found",
                    count=len(all_contracts),
                    contracts=all_contracts,
                )
                unique = {}
                for contract in all_contracts:
                    key = contract.get("contract_number") or contract.get(
                        "document_name"
                    )
                    unique[key] = contract

                contracts = list(unique.values())

                answer = build_contract_disambiguation(contracts)
                logger.debug("is_ambiguous_contract_query:answer", answer=answer)
                return {
                    "final_answer": answer,
                    "requires_clarification": True,
                    "agent_trace": {
                        "disambiguation": True,
                        "query_rewrite": {
                            "original_query": state.query,
                            "rewritten_query": rewritten_query,
                            "latency_ms": rewrite_latency_ms,
                            "enabled": self._settings.query_rewrite_enabled,
                        },
                    },
                    "total_tokens": getattr(state.query, "usage_metadata", {}).get(
                        "total_tokens", 0
                    ),
                    "citations": [],
                }

            logger.debug(
                "reranked docs",
                chunks=[
                    {"doc": c.document_name, "score": round(c.score, 3)}
                    for c in reranked[:5]
                ],
            )
            logger.debug(
                "rerank_output",
                docs=[
                    {
                        "doc": c.document_name,
                        "score": round(c.score, 3),
                    }
                    for c in reranked
                ],
            )
            latency = time.monotonic() - start_time
            logger.debug("rerank_chunks", latency=latency)

            # 4. Analyze context sufficiency
            start_time = time.monotonic()
            # context_str = self._format_context(reranked[:2])
            selected_chunks = self._select_context_chunks(
                reranked,
                max_chunks=5,
            )

            context_str = self._context_assembler.build(
                selected_chunks,
                limit=2,
            )
            latency = time.monotonic() - start_time
            logger.debug("self._format_context:", latency=latency)
            start_time = time.monotonic()
            analysis = await self._analyze_context(state.query, context_str)
            latency = time.monotonic() - start_time

            logger.debug("analize context time:", latency=latency)
            if not reranked:
                has_sufficient_context = False
                needs_research = True
            else:
                has_sufficient_context = analysis.get(
                    "has_sufficient_context",
                    True,
                )
                needs_research = analysis.get(
                    "needs_research",
                    not has_sufficient_context,
                )
            analysis["needs_research"] = needs_research
            analysis["has_sufficient_context"] = has_sufficient_context
            latency_ms = round((time.monotonic() - start) * 1000, 2)

            logger.debug(
                "retriever_agent_done",
                retrieved=len(chunks),
                reranked=len(reranked),
                sufficient=analysis.get("has_sufficient_context", False),
                latency_ms=latency_ms,
            )
            logger.debug(
                "final context",
                context=context_str,
            )
            return {
                "rewritten_query": rewritten_query,
                "retrieved_chunks": chunks,
                "reranked_chunks": reranked,
                "context_str": context_str,
                "has_sufficient_context": analysis.get(
                    "has_sufficient_context", bool(reranked)
                ),
                "needs_research": analysis.get("needs_research", False),
                "retrieval_latency_ms": latency_ms,
                "execution_path": ["retriever"],
                "agent_trace": {
                    "retriever": {
                        "query": rewritten_query,
                        "chunks_retrieved": len(chunks),
                        "chunks_reranked": len(reranked),
                        "latency_ms": latency_ms,
                    },
                    "query_rewrite": {
                        "original_query": state.query,
                        "rewritten_query": rewritten_query,
                        "latency_ms": rewrite_latency_ms,
                        "enabled": self._settings.query_rewrite_enabled,
                    },
                },
            }
        except Exception as e:
            logger.error("retriever_agent_error", error=str(e))
            raise

    async def _rewrite_query(self, state: AgentState) -> str:
        """Backward-compatible wrapper around QueryRewriter."""
        return await self._query_rewriter.rewrite(state)
    # async def _rewrite_query(self, state: AgentState) -> str:
    #     """Rewrite the query for better retrieval."""
    #     if any(term in state.query.lower() for term in PROTECTED_TERMS):
    #         logger.debug(
    #             "query rewrite skipped",
    #             query=state.query,
    #         )
    #
    #         return state.query
    #
    #     context = (
    #         "\n".join(f"{m.type}: {m.content[:200]}" for m in state.messages[-4:])
    #         if state.messages
    #         else "No prior context"
    #     )
    #
    #     chain = self._build_rewrite_chain()
    #     logger.debug(
    #         "query used for search",
    #         query=state.query,
    #     )
    #
    #     result = await chain.ainvoke(
    #         {
    #             "query": state.query,
    #             "conversation_context": context[:3000],
    #         }
    #     )
    #     content = result.content
    #
    #     if not isinstance(content, str):
    #         raise TypeError(f"Expected string response, got {type(content).__name__}")
    #     rewritten = content.strip()
    #
    #     logger.debug(
    #         "retrieval_query",
    #         original=state.query,
    #         rewritten=rewritten,
    #     )
    #
    #     return rewritten

    async def _analyze_context(self, query: str, context: str) -> dict:
        """Check if retrieved context is sufficient to answer the query."""
        if not context:
            return {"has_sufficient_context": False, "needs_research": False}

        chain = RETRIEVAL_ANALYSIS_TEMPLATE | self._llm
        result = await chain.ainvoke({"query": query, "context": context[:3000]})
        content = result.content

        if not isinstance(content, str):
            raise TypeError(f"Expected string response, got {type(content).__name__}")
        try:
            analysis = json.loads(content)
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
        context = "\n\n---\n\n".join(parts)
        return context[:MAX_CONTEXT]

    @staticmethod
    def _select_context_chunks(
            chunks: list[RetrievedChunk],
            max_chunks: int = 5,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        selected: list[RetrievedChunk] = []
        seen_documents = set()

        for chunk in chunks:
            if len(selected) >= max_chunks:
                break

            # Avoid filling the whole context with one document.
            if chunk.document_id not in seen_documents:
                selected.append(chunk)
                seen_documents.add(chunk.document_id)

        for chunk in chunks:
            if len(selected) >= max_chunks:
                break

            if chunk in selected:
                continue

            selected.append(chunk)

        return selected
