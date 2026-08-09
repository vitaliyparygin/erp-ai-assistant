import json
import time
from app.agents.state import AgentState
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import RetrievedChunk
from langchain_core.runnables import Runnable
from app.rag.prompts import (
    RETRIEVAL_ANALYSIS_TEMPLATE,
)
from app.rag.retriever.vector_retriever import VectorRetriever
from app.rag.retriever.reranker import Reranker
from app.ingestion.query_metadata import (
    extract_query_metadata,
    normalize_filter_metadata,
)
from app.retrieval.contracts import (
    get_unique_docs,
    requires_contract_disambiguation,
    build_contract_disambiguation,
)
from app.rag.query_rewriter import QueryRewriter
from app.config.constants import MAX_CONTEXT_ANALYSIS
from app.rag.context.assembler import ContextAssembler
from app.observability.metrics import (
    AGENT_EXECUTIONS_TOTAL,
    AGENT_LATENCY_SECONDS,
    RETRIEVAL_LATENCY_SECONDS,
    RERANK_LATENCY_SECONDS,
    CONTRACT_DISAMBIGUATIONS_TOTAL,
    RETRIEVAL_CHUNKS_RETURNED,
    CONTEXT_ANALYSIS_LATENCY_SECONDS,
    CONTEXT_ANALYSIS_TOTAL,
    QUERY_REWRITE_LATENCY_SECONDS,
    QUERY_REWRITE_TOTAL,
    RETRIEVAL_EMPTY_TOTAL
)



logger = get_logger(__name__)



class RetrieverAgent:
    """
    Semantic search agent.
    Rewrites the query, retrieves relevant chunks, and evaluates context sufficiency.
    """

    def __init__(
            self,
            llm: Runnable,
            retriever: VectorRetriever,
            reranker: Reranker,
            query_rewriter: QueryRewriter | None = None,
    ) -> None:
        self._llm = llm
        self._retriever = retriever
        self._reranker = reranker
        self._query_rewriter = query_rewriter or QueryRewriter(llm=llm)
        self._settings = get_settings()

        self._context_assembler = ContextAssembler(
            max_context=MAX_CONTEXT_ANALYSIS,
        )

    async def __call__(self, state: AgentState) -> dict:
        start = time.perf_counter()
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        logger.debug("retriever_agent_start", query=state.query[:60])
        try:
            # 1. Query rewriting
            rewrite_enabled = self._settings.query_rewrite_enabled
            rewrite_latency_seconds = 0.0

            if rewrite_enabled:
                rewrite_start = time.perf_counter()

                try:
                    rewritten_query, rewrite_usage = await self._rewrite_query(state)
                    QUERY_REWRITE_TOTAL.labels(
                        status="success",
                        method="llm",
                    ).inc()
                    input_tokens = rewrite_usage["input_tokens"]
                    output_tokens = rewrite_usage["output_tokens"]
                    total_tokens = rewrite_usage["total_tokens"]
                except Exception:
                    QUERY_REWRITE_TOTAL.labels(
                        status="error",
                        method="llm",
                    ).inc()
                    raise
                finally:
                    rewrite_latency_seconds = time.perf_counter() - rewrite_start
                    QUERY_REWRITE_LATENCY_SECONDS.observe(rewrite_latency_seconds)
            else:
                rewritten_query = state.query.strip().lower()

            rewrite_latency_ms = round(
                rewrite_latency_seconds * 1000,
                2,
            )

            logger.debug(
                "query_rewrite_completed",
                original=state.query,
                rewritten=rewritten_query,
                latency_ms=rewrite_latency_ms,
                enabled=rewrite_enabled,
            )

            logger.debug(
                "retrieval_query",
                original=state.query,
                rewritten=rewritten_query,
            )


            raw_query_metadata = extract_query_metadata(rewritten_query)

            query_metadata = normalize_filter_metadata(raw_query_metadata)

            logger.debug(
                "query_metadata_normalized",
                query=rewritten_query,
                query_metadata=query_metadata,
            )
            retrieval_start = time.perf_counter()

            chunks = await self._retriever.retrieve(
                query=rewritten_query,
                document_ids=[str(d) for d in state.document_ids] or None,
                query_metadata=query_metadata,
            )

            retrieval_latency = time.perf_counter() - retrieval_start

            RETRIEVAL_LATENCY_SECONDS.observe(retrieval_latency)
            RETRIEVAL_CHUNKS_RETURNED.observe(len(chunks))
            if not chunks:
                RETRIEVAL_EMPTY_TOTAL.inc()
                logger.warning(
                    "retrieval_empty",
                    query=rewritten_query,
                )
            logger.debug(
                "retrieval_completed",
                query=rewritten_query,
                chunks=len(chunks),
                latency_seconds=round(retrieval_latency, 4),
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
            logger.debug(
                "retrieval_stage_timing",
                latency_seconds=round(retrieval_latency, 4),
            )
            # 3. Reranking

            raw_chunk_count = len(chunks)
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

            logger.debug(
                "retrieval_dedup_completed",
                raw_chunks=raw_chunk_count,
                unique_chunks=len(chunks),
                duplicates_removed=raw_chunk_count - len(chunks),
            )
            logger.info(
                "retrieval_before_rerank",
                query=rewritten_query,
                candidates=[
                    {
                        "document": c.document_name,
                        "score": c.score,
                        "content": c.content[:300],
                    }
                    for c in chunks
                ],
            )
            rerank_start = time.perf_counter()
            reranked = await self._reranker.rerank(
                query=rewritten_query,
                chunks=chunks,
            )
            logger.info(
                "retrieval_after_rerank",
                query=rewritten_query,
                candidates=[
                    {
                        "document": c.document_name,
                        "score": c.score,
                    }
                    for c in reranked
                ],
            )
            rerank_latency = time.perf_counter() - rerank_start
            RERANK_LATENCY_SECONDS.observe(rerank_latency)
            logger.debug(
                "rerank_completed",
                input_chunks=len(chunks),
                output_chunks=len(reranked),
                latency_seconds=round(rerank_latency, 4),
            )

            unique_docs_after_rerank = get_unique_docs(reranked)
            logger.debug(
                "reranked_top_documents",
                docs=[
                    {
                        "doc": chunk.document_name,
                        "score": round(chunk.score, 3),
                    }
                    for chunk in reranked[:10]
                ],
            )
            logger.debug(
                "unique_docs_after_rerank",
                docs=list(unique_docs_after_rerank.keys()),
            )
            if requires_contract_disambiguation(
                state.query,
                reranked,
            ):
                CONTRACT_DISAMBIGUATIONS_TOTAL.labels(
                    status="success",
                ).inc()

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
                AGENT_EXECUTIONS_TOTAL.labels(
                    agent="retriever",
                    status="success",
                ).inc()
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
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
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
            logger.debug(
                "rerank_stage_timing",
                latency_seconds=round(rerank_latency, 4),
            )

            # 4. Analyze context sufficiency
            context_start = time.perf_counter()

            selected_chunks = self._select_context_chunks(
                reranked,
                max_chunks=5,
            )

            context_str = self._context_assembler.build(
                selected_chunks,
            )

            context_selection_latency = time.perf_counter() - context_start

            logger.debug(
                "context_assembled",
                reranked_chunks=len(reranked),
                selected_chunks=len(selected_chunks),
                context_length=len(context_str),
                latency_seconds=round(context_selection_latency, 4),
            )

            analysis_start = time.perf_counter()

            analysis = await self._analyze_context(
                state.query,
                context_str,
            )
            analysis_usage = getattr(analysis, "usage_metadata", {}) or {}
            input_tokens += analysis_usage.get("input_tokens", 0)
            output_tokens += analysis_usage.get("output_tokens", 0)
            total_tokens += analysis_usage.get("total_tokens", 0)

            analysis_latency = time.perf_counter() - analysis_start
            CONTEXT_ANALYSIS_LATENCY_SECONDS.observe(analysis_latency)


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

            CONTEXT_ANALYSIS_TOTAL.labels(
                result="needs_research" if needs_research else "sufficient"
            ).inc()

            analysis["needs_research"] = needs_research
            analysis["has_sufficient_context"] = has_sufficient_context

            total_latency_ms = round(
                (time.perf_counter() - start) * 1000,
                2,
            )

            retrieval_latency_ms = round(retrieval_latency * 1000, 2)
            rerank_latency_ms = round(rerank_latency * 1000, 2)
            context_analysis_latency_ms = round(analysis_latency * 1000, 2)

            logger.debug(
                "retriever_agent_done",
                retrieved=len(chunks),
                reranked=len(reranked),
                sufficient=analysis.get("has_sufficient_context", False),
                latency_ms=total_latency_ms,
                retrieval_latency_ms= round(retrieval_latency * 1000, 2),
                rerank_latency_ms= round(rerank_latency * 1000, 2),
                context_analysis_latency_ms= round(analysis_latency * 1000, 2),
                query_rewrite_latency_ms= round(rewrite_latency_ms, 2),
                vector_retrieval_latency_ms= retrieval_latency_ms
            )
            logger.info(
                "retriever_diagnostic",
                original_query=state.query,
                rewritten_query=rewritten_query,
                retrieved=[
                    {
                        "document_id": c.document_id,
                        "document_name": c.document_name,
                        "score": c.score,
                        "document_type": c.metadata.get("document_type"),
                    }
                    for c in chunks[:10]
                ],
                reranked=[
                    {
                        "document_id": c.document_id,
                        "document_name": c.document_name,
                        "score": c.score,
                        "document_type": c.metadata.get("document_type"),
                    }
                    for c in reranked[:10]
                ],

            )
            logger.debug(
                "final context",
                context=context_str,
            )
            AGENT_EXECUTIONS_TOTAL.labels(
                agent="retriever",
                status="success",
            ).inc()
            return {
                "rewritten_query": rewritten_query,
                "retrieved_chunks": chunks,
                "reranked_chunks": reranked,
                "context_str": context_str,
                "has_sufficient_context": has_sufficient_context,
                "needs_research": needs_research,
                "retrieval_latency_ms": retrieval_latency_ms,
                "execution_path": ["retriever"],
                "agent_trace": {
                    "retriever": {
                        "query": rewritten_query,
                        "chunks_retrieved": raw_chunk_count,
                        "chunks_after_dedup": len(chunks),
                        "chunks_reranked": len(reranked),
                        "latency_ms": total_latency_ms,
                        "retrieval_latency_ms": retrieval_latency_ms,
                        "rerank_latency_ms": rerank_latency_ms,
                        "context_analysis_latency_ms": context_analysis_latency_ms,
                    },
                    "query_rewrite": {
                        "original_query": state.query,
                        "rewritten_query": rewritten_query,
                        "latency_ms": rewrite_latency_ms,
                        "enabled": self._settings.query_rewrite_enabled,
                    },
                },
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }

        except Exception:
            AGENT_EXECUTIONS_TOTAL.labels(
                agent="retriever",
                status="error",
            ).inc()

            logger.exception(
                "retriever_agent_error",
            )

            raise

        finally:
            AGENT_LATENCY_SECONDS.labels(
                agent="retriever",
            ).observe(
                time.perf_counter() - start
            )

    async def _rewrite_query(
            self,
            state: AgentState,
    ) -> tuple[str, dict[str, int]]:
        return await self._query_rewriter.rewrite(state)


    async def _analyze_context(
            self,
            query: str,
            context: str,
    ) -> dict:
        """Check if retrieved context is sufficient to answer the query."""
        if not context:
            return {
                "has_sufficient_context": False,
                "needs_research": True,
            }

        chain = RETRIEVAL_ANALYSIS_TEMPLATE | self._llm

        result = await chain.ainvoke(
            {
                "query": query,
                "context": context,
            }
        )

        content = result.content

        if not isinstance(content, str):
            raise TypeError(
                f"Expected string response, got {type(content).__name__}"
            )

        try:
            analysis = json.loads(content)
        except Exception:
            logger.warning(
                "context_analysis_invalid_json",
                query=query,
            )
            return {
                "has_sufficient_context": True,
                "needs_research": False,
            }

        return analysis

    @staticmethod
    def _format_context(
            chunks: list[RetrievedChunk],
    ) -> str:
        return ContextAssembler(
            max_context=MAX_CONTEXT_ANALYSIS,
        ).build(chunks)

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
