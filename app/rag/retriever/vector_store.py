import uuid
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from app.core.config import get_settings
from app.core.exceptions import VectorStoreError
from app.core.logging import get_logger
from app.rag.chunker import TextChunk

logger = get_logger(__name__)


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
        original_filename: str | None,
    ) -> list[str]:
        """
        Upsert document chunks with their embeddings into Qdrant.
        Returns the list of point IDs created.
        """

        logger.debug(
            "upsert_debug",
            chunks=len(chunks),
            embeddings=len(embeddings),
            original_filename=original_filename,
        )

        if len(chunks) != len(embeddings):
            raise VectorStoreError("Chunks and embeddings count mismatch")

        point_ids: list[str] = []
        points: list[PointStruct] = []

        for chunk, embedding in zip(chunks, embeddings):
            logger.debug(
                "UPSERT_POINT", document=document_name, chunk_index=chunk.chunk_index
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
            logger.debug("UPSERT_POINT payload", payload=payload)
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
