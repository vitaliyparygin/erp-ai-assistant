"""
Qdrant-backed vector retriever.
Supports dense retrieval, hybrid (sparse+dense) search, metadata filtering,
and cross-encoder reranking.
"""
import time
import uuid
from typing import Any
import re
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    NamedVector,
    PointStruct,
    VectorParams,
)

from app.core.config import get_settings
from app.core.exceptions import RetrievalError, VectorStoreError
from app.core.logging import get_logger
from app.models.schemas import RetrievedChunk
from app.rag.chunker import TextChunk
from app.rag.embeddings import EmbeddingService

logger = get_logger(__name__)

TERM_EXPANSIONS = {
    "executor": {"contractor", "service provider"},
    "contractor": {"executor"},
    "customer": {"client"},
}
STOP_WORDS = {
    "the", "is", "with", "which",
    "a", "an", "of", "to", "in"
}
IMPORTANT_TERMS = {
    "contract",
    "contractor",
    "executor",
    "customer",
    "agreement",
}

DOCUMENT_HINTS = {
    "договір": {
        "service agreement",
        "contract number",
        "contractor",
    },
    "наказ": {
        "employee order",
        "employee",
    },
    "рахунок": {
        "invoice",
        "amount",
        "customer",
    },
}

class VectorStore:
    """
    Manages the Qdrant vector collection for document embeddings.
    Handles collection initialization, upsert, and lifecycle.
    """

    def __init__(self, client: AsyncQdrantClient) -> None:
        self._client = client
        self._settings = get_settings()
        self._collection = self._settings.qdrant_collection_name
        self._vector_size = self._settings.qdrant_vector_size

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection if it doesn't exist."""
        try:
            exists = await self._client.collection_exists(self._collection)
            if not exists:
                await self._client.create_collection(
                    collection_name=self._collection,
                    vectors_config=VectorParams(
                        size=self._vector_size,
                        distance=Distance.COSINE,
                        on_disk=True,
                    ),
                    optimizers_config=models.OptimizersConfigDiff(
                        indexing_threshold=20000,
                    ),
                )
                logger.info("qdrant_collection_created", collection=self._collection)
        except Exception as e:
            raise VectorStoreError(f"Failed to ensure collection: {e}") from e

    async def upsert_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        document_id: str,
        document_name: str,
    ) -> list[str]:
        """
        Upsert document chunks with their embeddings into Qdrant.
        Returns the list of point IDs created.
        """

        logger.debug(
            "upsert_debug",
            chunks=len(chunks),
            embeddings=len(embeddings),
        )

        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunks and embeddings count mismatch")

        point_ids: list[str] = []
        points: list[PointStruct] = []

        for chunk, embedding in zip(chunks, embeddings):
            logger.debug(
                "UPSERT_POINT",
                document=document_name,
                chunk_index=chunk.chunk_index,
            )
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)

            payload = {
                "document_id": document_id,
                "document_name": document_name,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "chunk_metadata": chunk.metadata,
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

        try:
            await self._client.upsert(
                collection_name=self._collection,
                points=points,
                wait=True,
            )
            logger.debug(
                "chunks_upserted",
                document_id=document_id,
                count=len(points),
                collection=self._collection,
            )
        except Exception as e:
            raise VectorStoreError(f"Qdrant upsert failed: {e}") from e

        return point_ids

    async def delete_document(self, document_id: str) -> None:
        """Remove all chunks belonging to a document from Qdrant."""
        try:
            await self._client.delete(
                collection_name=self._collection,
                points_selector=models.FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="document_id",
                                match=MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            logger.info("document_deleted_from_qdrant", document_id=document_id)
        except Exception as e:
            raise VectorStoreError(f"Failed to delete document from Qdrant: {e}") from e


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
            type_first_item=type(query_embedding[0])
        )
        logger.debug(
            "QUERY_EMBEDDING",
            dim=len(query_embedding),
            first=query_embedding[:10],
        )
        # Build optional document filter
        search_filter: Filter | None = None
        if document_ids:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchAny(any=document_ids),
                    )
                ]
            )

        try:
            logger.debug(
                "query_embedding_type",
                type=str(type(query_embedding)),
            )

            logger.debug(
                "query_embedding_len",
                len=len(query_embedding)
            )
            logger.debug(
                "query_embedding_threshold",
                threshold=threshold
            )
            logger.debug(
                "query_embedding_first",
                value=query_embedding[:5],
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
                logger.debug(
                    "retrieved_doc",
                    score=hit.score,
                    chunk=hit.payload["content"][:200]
                )
                logger.debug(
                    "QDRANT_RESULTS",
                    docs=[
                        {
                            "doc": p.payload.get("document_name"),
                            "score": p.score,
                        }
                        for p in results
                    ]
                )
            logger.debug(
                "retrieval_debug",
                found=len(results),
            )
            count = await self._client.count(
                collection_name="erp_documents"
            )
            logger.debug(
                "count erp_documents",
                found=count,
            )


        except Exception as e:
            raise RetrievalError(f"Qdrant search failed: {e}") from e

        latency_ms = (time.monotonic() - start_time) * 1000

        chunks = [
            RetrievedChunk(
                chunk_id=str(result.id),
                document_id=result.payload.get("document_id", ""),
                document_name=result.payload.get("document_name", ""),
                content=result.payload.get("content", ""),
                page_number=result.payload.get("page_number"),
                score=result.score,
                chunk_index=result.payload.get("chunk_index", 0),
                metadata=result.payload.get("chunk_metadata", {}),
            )
            for result in results
        ]

        logger.debug(
            "retrieval_completed",
            query_preview=query[:60],
            retrieved=len(chunks),
            latency_ms=round(latency_ms, 2),
            top_score=chunks[0].score if chunks else 0,
        )

        if query.lower().startswith("debug:"):
            return {
                "retrieved_chunks": chunks,
                "execution_path": ["retriever"],
            }
        return chunks


class Reranker:
    """
    Reranks retrieved chunks using an LLM-based cross-encoder approach.
    Falls back to score-based ranking when LLM reranking is disabled.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """
        Rerank chunks by relevance to the query.
        Uses a simple relevance scoring approach; swap in a cross-encoder
        (e.g. Cohere Rerank) for production-grade reranking.
        """
        start_time = time.monotonic()
        k = top_k or self._settings.rag_rerank_top_k
        logger.debug(
            "rerank start",
            chunks=chunks,
            query=query,
            top_k=top_k,
            k=k
        )

        if not chunks:
            return []

        # Score-based reranking: boost chunks where query terms appear
        query_terms = {
            t
            for t in re.findall(r"\w+", query.lower())
            if t not in STOP_WORDS
        }
        expanded_terms = set(query_terms)

        for term in list(query_terms):
            expanded_terms.update(
                TERM_EXPANSIONS.get(term, set())
            )
        logger.debug(
            "rerank query_terms",
            query_terms=query_terms
        )

        def rerank_score(chunk: RetrievedChunk) -> float:
            content_lower = chunk.content.lower()

            score = chunk.score

            content_terms = set(
                re.findall(r"\w+", content_lower)
            )

            # common coincidences of terms
            term_matches = len(expanded_terms & content_terms)
            score += min(
                term_matches / max(len(expanded_terms), 1),
                0.2,
            )

            # spec ERP-field
            if "customer" in expanded_terms:
                if "customer:" in content_lower:
                    score += 0.25

            if {"contractor", "executor"} & expanded_terms:
                if "contractor:" in content_lower:
                    score += 0.35

            if "contract" in expanded_terms:
                if "service agreement" in content_lower:
                    score += 0.50

                if "contract number" in content_lower:
                    score += 0.30

                if "contractor:" in content_lower:
                    score += 0.20

                if "customer:" in content_lower:
                    score += 0.10

                if "invoice" in content_lower:
                    score -= 0.20

            # extra weight for important terms
            for term in expanded_terms:
                if term in content_terms:
                    score += 0.05

                    if term in IMPORTANT_TERMS:
                        score += 0.15
                for hint in DOCUMENT_HINTS.get(term, []):
                    if hint in content_lower:
                        score += 0.2
            logger.debug(
                "rerank document_name+score",
                document_name=chunk.document_name,
                score=score,
                chunk_score=chunk.score
            )

            return score

        logger.debug(
            "rerank.chunks:",
            chunks=[
                {
                    "doc": c.document_name,
                    "score": round(c.score, 3)
                }
                for c in chunks
            ]
        )
        reranked = sorted(chunks, key=rerank_score, reverse=True)
        logger.debug(
            "rerank reranked",
            reranked=reranked,
            reranked_k=reranked[:k]
        )

        return reranked[:k]