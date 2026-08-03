import time
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)

from app.core.config import get_settings
from app.core.exceptions import RetrievalError
from app.core.logging import get_logger
from app.models.schemas import RetrievedChunk
from app.rag.embeddings import EmbeddingService
from app.config.constants import METADATA_FILTER_FIELDS
from qdrant_client.models import Condition

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

        start_time = time.monotonic()
        k = top_k or self._settings.rag_top_k

        threshold = score_threshold or self._settings.rag_score_threshold
        logger.debug(
            "RETRIEVER_CALLED",
            query=query,
        )
        # Generate query embedding
        query_embedding = await self._embedder.embed_text(query)

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
        # search_filter = build_retrieval_filter(
        #     query_metadata=query_metadata,
        #     document_ids=document_ids,
        # )
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
            response = await self._client.query_points(
                collection_name=self._collection,
                query=query_embedding,
                limit=k,
                query_filter=search_filter,
                score_threshold=threshold,
                with_payload=True,
            )

            logger.debug(
                "RAW RESPONSE:",
                response=response,
            )
            results = response.points
            for hit in results:
                payload = hit.payload
                if not payload:
                    continue
                logger.debug(
                    "retrieved_doc",
                    score=hit.score,
                    chunk=str(payload.get("content", ""))[:200],
                )
                logger.debug(
                    "QDRANT_RESULTS",
                    docs=[
                        {
                            "doc": payload.get("document_name"),
                            "score": p.score,
                        }
                        for p in results
                    ],
                )
            logger.debug(
                "retrieval_debug",
                found=len(results),
            )
            count = await self._client.count(collection_name="erp_documents")
            logger.debug(
                "count erp_documents",
                found=count,
            )

        except Exception as e:
            raise RetrievalError(f"Qdrant search failed: {e}") from e

        latency_ms = (time.monotonic() - start_time) * 1000

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
        logger.debug(
            "RETRIEVER_RESULTS",
            docs=[
                {
                    "name": c.metadata.get("document_name"),
                    "type": c.metadata.get("document_type"),
                    "score": c.score,
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

        return Filter(must=must)
