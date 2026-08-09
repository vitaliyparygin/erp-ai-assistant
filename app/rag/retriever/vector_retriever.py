import time
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)
from app.observability.metrics import (
    EMBEDDING_REQUESTS_TOTAL,
    EMBEDDING_LATENCY_SECONDS,
    RETRIEVAL_REQUESTS_TOTAL,
    QDRANT_SEARCH_LATENCY_SECONDS,
)
from app.core.config import get_settings
from app.core.exceptions import RetrievalError
from app.core.logging import get_logger
from app.models.schemas import RetrievedChunk
from app.rag.embeddings import EmbeddingService
from qdrant_client.models import Condition
from app.config.constants import (
    METADATA_FILTER_FIELDS,
    PROTECTED_IDENTIFIER_PATTERN,
)
from qdrant_client.models import ScoredPoint

logger = get_logger(__name__)


class VectorRetriever:
    """
    Semantic retrieval from Qdrant with optional metadata filtering,
    query rewriting, and score-based filtering.
    """

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embedding_service: EmbeddingService,
    ) -> None:
        self._client = qdrant_client
        self._embedder = embedding_service
        self._settings = get_settings()
        self._collection = self._settings.qdrant_collection_name

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        document_ids: list[str] | None = None,
        score_threshold: float | None = None,
        query_metadata: dict | None = None,
    ) -> list[RetrievedChunk]:
        """
        Perform semantic vector search against the document collection.

        Args:
            query: The search query text.
            top_k: Number of results to return.
            document_ids: Optional list to restrict search to specific documents.
            score_threshold: Minimum similarity score (0-1).

        Returns:
            List of RetrievedChunk sorted by relevance score descending.
        """

        start = time.perf_counter()
        k = top_k or self._settings.rag_top_k

        threshold = (
            self._settings.rag_score_threshold
            if score_threshold is None
            else score_threshold
        )
        logger.debug(
            "RETRIEVER_CALLED",
            query=query,
        )
        # Generate query embedding
        embedding_start = time.perf_counter()

        try:
            query_embedding = await self._embedder.embed_text(query)

            embedding_latency = time.perf_counter() - embedding_start

            EMBEDDING_REQUESTS_TOTAL.labels(
                status="success",
            ).inc()
            from prometheus_client import REGISTRY

            print(
                "QDRANT METRIC DEBUG:",
                "object_id=",
                id(QDRANT_SEARCH_LATENCY_SECONDS),
                "type=",
                type(QDRANT_SEARCH_LATENCY_SECONDS),
                "name=",
                QDRANT_SEARCH_LATENCY_SECONDS._name,
                "qdrant_latency=",
                embedding_latency,
            )

            print(
                "REGISTERED:",
                "qdrant_search_latency_seconds" in REGISTRY._names_to_collectors,
            )

            print(
                "COLLECTOR:",
                REGISTRY._names_to_collectors.get("erp_qdrant_search_latency_seconds"),
            )
            EMBEDDING_LATENCY_SECONDS.observe(
                embedding_latency,
            )

        except Exception:
            EMBEDDING_REQUESTS_TOTAL.labels(
                status="error",
            ).inc()

            raise

        logger.debug(
            "query_embedding_debug",
            len=len(query_embedding),
            type=type(query_embedding),
            type_first_item=type(query_embedding[0]),
        )
        logger.debug(
            "QUERY_EMBEDDING",
            dim=len(query_embedding),
            first=query_embedding[:10],
        )
        # Build optional document filter

        search_filter = self.get_filter_condition(query_metadata, document_ids)
        logger.info(
            "semantic_search_filter",
            query=query,
            query_metadata=query_metadata,
            document_ids=document_ids,
            search_filter=search_filter,
        )

        try:
            logger.debug(
                "query_embedding_type",
                type=str(type(query_embedding)),
            )

            logger.debug("query_embedding_len", len=len(query_embedding))
            logger.debug("query_embedding_threshold", threshold=threshold)
            logger.debug(
                "query_embedding_first",
                value=query_embedding[:5],
            )
            logger.debug(
                "RETRIEVER_QUERY",
                query=query,
                query_filter=search_filter,
            )

            qdrant_start = time.perf_counter()

            logger.info(
                "semantic_search_parameters",
                query=query,
                top_k=k,
                score_threshold=threshold,
                has_filter=search_filter is not None,
            )

            try:
                response = await self._client.query_points(
                    collection_name=self._collection,
                    query=query_embedding,
                    limit=k,
                    query_filter=search_filter,
                    score_threshold=threshold,
                    with_payload=True,
                )
            finally:
                qdrant_latency = time.perf_counter() - qdrant_start

                QDRANT_SEARCH_LATENCY_SECONDS.observe(qdrant_latency)

                logger.debug(
                    "qdrant_query_completed",
                    latency_seconds=round(qdrant_latency, 4),
                )
            logger.debug(
                "semantic_retrieval_results",
                query=query,
                results=[self._payload_preview(point) for point in response.points],
            )
            semantic_results = response.points

            identifier = self._extract_identifier(query)
            logger.info(
                "identifier_extraction",
                query=query,
                identifier=identifier,
            )
            identifier_results = []
            if identifier:
                identifier_results = await self.search_by_identifier(identifier)

            logger.info(
                "retriever_identifier_results",
                original_query=query,
                identifier=identifier,
                results=[
                    {
                        "document_id": r.id,
                        "document_name": (r.payload or {}).get('original_filename'),
                        "score": r.score,
                    }
                    for r in identifier_results
                ],
            )
            if identifier_results:
                results = identifier_results + [
                    result
                    for result in semantic_results
                    if str(result.id) not in {str(r.id) for r in identifier_results}
                ]
            else:
                results = semantic_results

            logger.debug(
                "qdrant_query_completed",
                latency_seconds=round(qdrant_latency, 4),
                results=len(response.points),
            )
            logger.info(
                "retriever_identifier_results",
                original_query=query,
                identifier=identifier,
                results=[
                    {
                        "document_id": r.id,
                         "document_name": (r.payload or {}).get('original_filename'),
                        "score": None,
                    }
                    for r in identifier_results
                ],
            )

            logger.debug(
                "retrieval_debug",
                found=len(results),
            )

        except Exception as e:
            RETRIEVAL_REQUESTS_TOTAL.labels(
                status="error",
            ).inc()

            raise RetrievalError(f"Qdrant search failed: {e}") from e

        latency_ms = (time.monotonic() - start) * 1000

        chunks = []

        for result in results:
            res_payload = result.payload

            if res_payload is None:
                continue

            logger.debug(
                "RAW_QDRANT_PAYLOAD",
                payload=res_payload,
            )

            chunks.append(
                RetrievedChunk(
                    chunk_id=str(result.id),
                    document_id=res_payload.get("document_id", ""),
                    document_name=res_payload.get("original_filename", ""),
                    content=res_payload.get("content", ""),
                    page_number=res_payload.get("page_number"),
                    score=result.score,
                    chunk_index=res_payload.get("chunk_index", 0),
                    metadata=res_payload,
                )
            )

        RETRIEVAL_REQUESTS_TOTAL.labels(
            status="success",
        ).inc()
        logger.debug(
            "RETRIEVER_RESULTS",
            docs=[
                {
                    "name": c.document_name,
                    "type": c.metadata.get("document_type"),
                    "score": None,
                }
                for c in chunks[:10]
            ],
        )
        logger.debug(
            "retrieval_completed",
            query_preview=query[:60],
            retrieved=len(chunks),
            latency_ms=round(latency_ms, 2),
            top_score=chunks[0].score if chunks else 0,
        )

        if query.lower().startswith("debug:"):
            logger.debug(
                "retriever_debug",
                retrieved_chunks=chunks,
                execution_path=["retriever"],
            )
        return chunks

    async def get_contract_documents(self):
        logger.debug("get_contract_documents started")
        points, _ = await self._client.scroll(
            collection_name=self._collection,
            limit=100,
            with_payload=True,
        )
        contracts = {}

        for point in points:
            md = point.payload

            if md.get("document_type") != "contract":
                continue

            contracts[md["document_name"]] = {
                "document_name": md["document_name"],
                "contract_number": md.get("contract_number"),
                "valid_until": md.get("valid_until"),
            }
        logger.debug("get_contract_documents:", len_contracts=len(contracts))
        return list(contracts.values())

    async def search_by_identifier(
        self,
        identifier: str,
    ) -> list[ScoredPoint]:
        response = await self._client.scroll(
            collection_name=self._collection,
            scroll_filter=Filter(
                should=[
                    FieldCondition(
                        key="contract_number",
                        match=MatchValue(value=identifier),
                    ),
                    FieldCondition(
                        key="invoice_number",
                        match=MatchValue(value=identifier),
                    ),
                    FieldCondition(
                        key="original_filename",
                        match=MatchValue(value=identifier),
                    ),
                    FieldCondition(
                        key="stored_filename",
                        match=MatchValue(value=identifier),
                    ),
                ]
            ),
            limit=20,
            with_payload=True,
            with_vectors=False,
        )

        records, _ = response

        return [
            ScoredPoint(
                id=record.id,
                version=0,
                score=1.0,
                payload=record.payload,
                vector=None,
            )
            for record in records
        ]

    def get_filter_condition(
        self,
        query_metadata: dict | None = None,
        document_ids: list[str] | None = None,
    ) -> Filter | None:
        must: list[Condition] = []

        if document_ids:
            must.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids),
                )
            )

        if query_metadata:
            for key, value in query_metadata.items():
                if key not in METADATA_FILTER_FIELDS:
                    continue

                if not value:
                    continue

                must.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )

        if not must:
            return None

        search_filter = Filter(must=must)

        logger.info(
            "metadata_filter_built",
            query_metadata=query_metadata,
            document_ids=document_ids,
            filter=search_filter,
        )

        return search_filter

    @staticmethod
    def merge_results(
        identifier_results,
        semantic_results,
    ):
        merged = []
        seen = set()

        for result in identifier_results + semantic_results:
            result_id = str(result.id)

            if result_id in seen:
                continue

            seen.add(result_id)
            merged.append(result)

        return merged

    @staticmethod
    def _extract_identifier(query: str) -> str | None:
        match = PROTECTED_IDENTIFIER_PATTERN.search(query)

        if not match:
            return None

        return match.group(0).upper()

    @staticmethod
    def _payload_preview(point) -> dict:
        payload = point.payload

        if payload is None:
            return {
                "id": str(point.id),
                "document": None,
                "score": point.score,
                "content": "",
            }

        return {
            "id": str(point.id),
            "document": payload.get("original_filename"),
            "score": point.score,
            "content": payload.get("content", "")[:200],
        }
