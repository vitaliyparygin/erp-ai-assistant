"""
Qdrant-backed vector retriever.
Supports dense retrieval, hybrid (sparse+dense) search, metadata filtering,
and cross-encoder reranking.
"""
import time
import uuid
from typing import Any
import re

from dotenv.cli import unset
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
from app.rag.query_expansion import expand_query
from app.rag.bm25_reranker import BM25Reranker

logger = get_logger(__name__)

TERM_EXPANSIONS = {
    "executor": {"contractor", "service provider"},
    "угода": {
        "contract",
        "agreement",
        "opportunity",
        "stage",
    },
    "стадія": {
        "stage",
        "status",
        "phase",
    },
    "stage": [
        "стадія",
        "status",
        "етап",
        "phase",
    ],

    "customer": [
        "замовник",
        "клієнт",
        "customer",
        "executor"
    ],

    "contractor": [
        "виконавець",
        "підрядник",
        "contractor",
    ],

    "opportunity": [
        "угода",
        "deal",
        "opportunity",
    ],
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
    "customer": {
        "service_contract.pdf": 0.40,
        "Customer Card.pdf": 0.30,
    },

    "contractor": {
        "service_contract.pdf": 0.50,
    },

    "eic": {
        "electricity_bill.pdf": 0.80,
    },

    "stage": {
        "CRM Opportunity.pdf": 0.80,
    },

    "opportunity": {
        "CRM Opportunity.pdf": 0.80,
    },
}
keywords = {
    "telegram",
    "whatsapp",
    "viber",
    "assistance",
    "insurance",
    "policy"
}
FILTER_FIELDS = {
    "ticket_number",
    "purchase_order",
    "invoice_number",
    "employee_name",
    "customer",
    "contract_number",
    "policy_number",
    "agreement_number",
    "project",
    "department",
    "asset",
    "project_name",
    "original_filename"
}
IDENTIFIER_RE = re.compile(
    r"""
    \b(
        PO-\d{4}-\d+|
        INV-\d{4}-\d+|
        SC-\d{4}-\d+|
        ERP-\d{4}-\d+|
        VEND-\d{4}-\d+|
        DN-\d{4}-\d+
    )\b
    """,
    re.I | re.X,
)

def has_identifier(query: str):
    return bool(IDENTIFIER_RE.search(query))

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
        original_filename: str
    ) -> list[str]:
        """
        Upsert document chunks with their embeddings into Qdrant.
        Returns the list of point IDs created.
        """

        logger.debug(
            "upsert_debug",
            chunks=len(chunks),
            embeddings=len(embeddings),
            original_filename=original_filename
        )

        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunks and embeddings count mismatch")

        point_ids: list[str] = []
        points: list[PointStruct] = []

        for chunk, embedding in zip(chunks, embeddings):
            logger.debug(
                "UPSERT_POINT",
                document=document_name,
                chunk_index=chunk.chunk_index
            )
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)

            payload = {
                "document_id": document_id,
                "document_name": original_filename,
                "original_filename": original_filename,
                "stored_filename": document_name,
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "chunk_metadata": chunk.metadata,
                **chunk.metadata,


            }
            logger.debug(
                "UPSERT_POINT payload",
                payload=payload
            )
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
        self.bm25 = BM25Reranker()

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
        if has_identifier(query):
            q = query
        else:
            q = expand_query(query)


        logger.debug(
            "expand_query(query)",
            query=query,
            q=q
        )
        query_embedding = await self._embedder.embed_text(q)
        logger.warning(
            "EMBEDDING_HASH",
            hash=hash(tuple(round(x, 5) for x in query_embedding[:100])),
        )
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
        logger.debug(
            "query_metadata before self.get_filter_condition",
            query_metadata=query_metadata,
        )
        logger.warning(
            "CALL",
            query_metadata=id(query_metadata),
            value=query_metadata,
        )
        search_filter = self.get_filter_condition( query_metadata, document_ids)

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
            logger.warning(
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
            logger.warning(
                "RAW_QDRANT_RESULTS",
                docs=[
                    {
                        "doc": p.payload.get("original_filename"),
                        "score": p.score,
                        "text": p.payload.get("content", "")[:150],
                    }
                    for p in response.points
                ],
            )
            if not response and search_filter is not None:
                logger.warning(
                    "FILTER_EMPTY_FALLBACK",
                    filter=search_filter,
                )

                response = await self._client.query_points(
                    collection_name=self._collection,
                    query=query_embedding,
                    limit=30,
                    query_filter=None,
                    score_threshold=threshold,
                    with_payload=True,
                )

            logger.debug(
                "RAW RESPONSE:",
                response=response,
            )
            results = response.points

            results = self.bm25.rerank(
                query,
                results,
            )

            logger.debug(
                "bm25",
                bm25=results,
            )

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

        # chunks = [
        #     RetrievedChunk(
        #         chunk_id=str(result.id),
        #         document_id=result.payload.get("document_id", ""),
        #         document_name=result.payload.get("document_name", ""),
        #         content=result.payload.get("content", ""),
        #         page_number=result.payload.get("page_number"),
        #         score=result.score,
        #         chunk_index=result.payload.get("chunk_index", 0),
        #         metadata=result.payload.get("chunk_metadata", {}),
        #     )
        #
        #     for result in results
        # ]
        chunks = []

        for result in results:
            logger.warning(
                "RAW_QDRANT_PAYLOAD",
                payload=result.payload,
            )

            chunks.append(
                RetrievedChunk(
                    chunk_id=str(result.id),
                    document_id=result.payload.get("document_id", ""),
                    document_name=result.payload.get("original_filename", ""),
                    content=result.payload.get("content", ""),
                    page_number=result.payload.get("page_number"),
                    score=result.score,
                    chunk_index=result.payload.get("chunk_index", 0),
                    metadata=result.payload,
                )
            )
        logger.warning(
            "RETRIEVER_RESULTS",
            docs=[
                {
                    "name": c.metadata.get("document_name"),
                    "type": c.metadata.get("document_type"),
                    "score": c.score,
                }
                for c in chunks[:10]
            ]
        )
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

    async def get_contract_documents(self):
        logger.debug(
            "get_contract_documents started"
        )
        points, _ = await (self._client.scroll(
            collection_name=self._collection,
            limit=100,
            with_payload=True,
        ))
        print("GET_CONTRACT_DOCUMENTS CALLED")
        contracts = {}

        for point in points:

            md = point.payload

            if md.get("document_type") != "contract":
                continue

            contracts[
                md["document_name"]
            ] = {
                "document_name": md["document_name"],
                "contract_number": md.get("contract_number"),
                "valid_until": md.get("valid_until"),
            }
        logger.debug(
            "get_contract_documents:",
            len_contracts=len(contracts)
        )
        return list(contracts.values())


    def get_filter_condition(self, query_metadata=None, document_ids=None):
        print(id(query_metadata), query_metadata)
        must = []
        print(f"get_filter_condition started query_metadata={query_metadata}")


        if query_metadata:
            query_metadata.pop("person", None)
            must = self.build_qdrant_filter(query_metadata)
        logger.warning(
            "get_filter_condition",
            must=must,
        )
        if document_ids:
            must.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids),
                )
            )
        if not must:
            return None

        return Filter(must=must)

    def build_qdrant_filter(self, query_metadata: dict) -> dict | None:
        conditions = []

        for key, value in query_metadata.items():
            if key in FILTER_FIELDS and value:
                if key == "intent":
                    continue
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )
        logger.warning(
            "build_qdrant_filter",
            conditions=conditions,
        )
        if not conditions:
            return None

        return conditions


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
            FIELD_HINTS = {
                "customer": ["customer:"],
                "contractor": ["contractor:"],
                "executor": ["contractor:"],
                "eic": ["eic"],
                "stage": ["stage:"],
                "status": ["status:"],
            }
            content_lower = chunk.content.lower()

            score = chunk.score
            for term in expanded_terms:

                if term not in FIELD_HINTS:
                    continue

                markers = FIELD_HINTS[term]

                for marker in markers:

                    if marker in content_lower:
                        score += 1.0
                        break
            content_terms = set(
                re.findall(r"\w+", content_lower)
            )

            # common coincidences of terms
            term_matches = len(expanded_terms & content_terms)
            score += min(
                term_matches / max(len(expanded_terms), 1),
                0.2,
            )
            print('-= expanded_terms =-')
            print(expanded_terms)
            # spec ERP-field


            if "eic" in expanded_terms:
                if "eic" in content_lower:
                    score += 0.50

            if "customer" in expanded_terms:
                if "customer:" in content_lower:
                    score += 0.40

            if {"contractor", "executor"} & expanded_terms:
                if "contractor:" in content_lower:
                    score += 0.40

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
            if "stage" in expanded_terms:
                if "stage:" in content_lower:
                    score += 0.40
            # extra weight for important terms
            for term in expanded_terms:
                if term in content_terms:
                    score += 0.05

                    if term in IMPORTANT_TERMS:
                        score += 0.15
                if term in DOCUMENT_HINTS:
                    boosts = DOCUMENT_HINTS[term]

                    if chunk.document_name in boosts:
                        score += boosts[chunk.document_name]
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