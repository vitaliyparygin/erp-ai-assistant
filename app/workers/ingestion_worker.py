"""
Celery workers for async document ingestion.
Handles the full pipeline: parse → chunk → embed → index.
"""
import time
import uuid
from pathlib import Path

from celery.utils.log import get_task_logger

from app.core.config import get_settings
from app.workers.celery_app import celery_app

settings = get_settings()

task_logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="ingest_document",
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=300,
    time_limit=360,
)
def ingest_document(
    self,
    document_id: str,
    file_path: str,
    mime_type: str,
    document_name: str,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> dict:
    """
    Full document ingestion pipeline:
    1. Parse document (PDF/DOCX/TXT)
    2. Chunk into overlapping segments
    3. Generate embeddings
    4. Index in Qdrant
    5. Update PostgreSQL status

    This is an async task run in a sync Celery context.
    Uses asyncio.run() to execute the async pipeline.
    """
    print("INGESTION TASK STARTED")
    print("DOCUMENT ID:", document_id)
    import asyncio
    # loop = asyncio.new_event_loop()
    # asyncio.set_event_loop(loop)

    try:
        return asyncio.run(
            _ingest_document_async(
                task=self,
                document_id=document_id,
                file_path=file_path,
                mime_type=mime_type,
                document_name=document_name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    except Exception as e:
        task_logger.exception(e)
        raise e



async def _ingest_document_async(
    task,
    document_id: str,
    file_path: str,
    mime_type: str,
    document_name: str,
    chunk_size: int | None,
    chunk_overlap: int | None,
) -> dict:
    """Async implementation of the ingestion pipeline."""
    from app.core.logging import get_logger
    from app.db.session import AsyncSessionLocal
    from app.models.orm import DocumentModel
    from app.observability.metrics import (
        DOCUMENTS_INGESTED_TOTAL,
        INGESTION_CHUNKS_CREATED,
        INGESTION_LATENCY_SECONDS,
    )
    from app.rag.chunker import DocumentChunker, DocumentParser
    from app.rag.embeddings import EmbeddingService
    from app.rag.retriever import VectorStore
    from qdrant_client import AsyncQdrantClient
    from sqlalchemy import select

    logger = get_logger(__name__)
    start_time = time.monotonic()

    logger.info(
        "ingestion_started",
        document_id=document_id,
        file_path=file_path,
        mime_type=mime_type,
    )

    try:
        # ---- Parse ----
        parser = DocumentParser()
        parsed_doc = parser.parse(file_path, mime_type)

        # ---- Chunk ----
        chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        chunks = chunker.chunk(parsed_doc, document_id)

        if not chunks:
            raise ValueError(f"No chunks extracted from document {document_id}")

        # ---- Embed ----
        embedding_service = EmbeddingService()
        texts = [chunk.content for chunk in chunks]
        embeddings = await embedding_service.embed_batch(texts)

        logger.warning(
            "ingestion_debug",
            chunks=len(chunks),
            texts=len(texts),
        )

        logger.warning(
            "embedding_debug",
            embeddings=len(embeddings),
        )
        # ---- Index in Qdrant ----
        qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
        vector_store = VectorStore(qdrant_client)
        await vector_store.ensure_collection()

        logger.warning(
            "DOCUMENT_CHUNKS",
            document=document_name,
            count=len(chunks),
        )
        for i, chunk in enumerate(chunks):
            logger.warning(
                "CHUNK",
                document=document_name,
                index=i,
                content=chunk.content[:300]
            )
        point_ids = await vector_store.upsert_chunks(
            chunks=chunks,
            embeddings=embeddings,
            document_id=document_id,
            document_name=document_name,
        )
        logger.warning(
            "QDRANT_UPSERT",
            document=document_name,
            chunks=len(chunks),
            points=len(point_ids),
        )
        await qdrant_client.close()

        # ---- Update DB ----
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(DocumentModel).where(
                    DocumentModel.id == uuid.UUID(document_id)
                )
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "indexed"
                doc.chunk_count = len(chunks)
                doc.page_count = parsed_doc.total_pages
                doc.qdrant_collection = settings.qdrant_collection_name
                await db.commit()

        # ---- Metrics ----
        latency = time.monotonic() - start_time
        DOCUMENTS_INGESTED_TOTAL.labels(status="success", mime_type=mime_type).inc()
        INGESTION_CHUNKS_CREATED.observe(len(chunks))
        INGESTION_LATENCY_SECONDS.observe(latency)

        logger.info(
            "ingestion_completed",
            document_id=document_id,
            chunks=len(chunks),
            pages=parsed_doc.total_pages,
            latency_s=round(latency, 2),
        )
        logger.info(
            "DOCUMENT_CHUNKS",
            file=document_name,
            chunks=len(chunks)
        )
        return {
            "document_id": document_id,
            "status": "indexed",
            "chunks": len(chunks),
            "pages": parsed_doc.total_pages,
            "latency_s": round(latency, 2),
        }

    except Exception as exc:
        logger.error("ingestion_failed", document_id=document_id, error=str(exc))

        # Update DB with error
        try:
            # await db.rollback()
            #
            # raise
            from app.db.session import AsyncSessionLocal
            from app.models.orm import DocumentModel
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(DocumentModel).where(
                        DocumentModel.id == uuid.UUID(document_id)
                    )
                )
                doc = result.scalar_one_or_none()
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(exc)[:500]
                    await db.commit()
        except Exception as exc:
            logger.error(
                "ingestion_worker. ",
                error=str(e),
                error_type=type(e).__name__,
            )
            import traceback
            traceback.print_exc()
            raise

        DOCUMENTS_INGESTED_TOTAL.labels(status="error", mime_type=mime_type).inc()

        # Retry with exponential backoff
        raise task.retry(exc=exc, countdown=2 ** task.request.retries * 30)
