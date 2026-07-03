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
import inspect
from app.db.session import AsyncSessionLocal
from app.models.orm import DocumentModel,DocumentChunkModel
from sqlalchemy import select
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
    original_filename: str | None = None,
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
                original_filename=original_filename
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
    original_filename:str | None = None,
) -> dict:
    """Async implementation of the ingestion pipeline."""
    from app.core.logging import get_logger
    from app.db.session import get_sessionmaker
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
    logger.warning(
        "CHUNKER_CLASS",
        file=inspect.getfile(DocumentChunker),
    )
    logger.info(
        "ingestion_started",
        document_id=document_id,
        file_path=file_path,
        mime_type=mime_type
    )
    logger.warning(
        "INGEST_START",
        document_id=document_id,
        document_name=document_name,
    )
    try:
        # ---- Parse ----
        parser = DocumentParser()
        parsed_doc = parser.parse(file_path, mime_type)


        # ---- Chunk ----
        print(
            "DocumentChunker source:",
            inspect.getfile(DocumentChunker),
        )
        chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        print(
            "ingestion_worker chunks begin"
        )
        chunks = chunker.chunk(parsed_doc, document_id)

        # print('db_chunks:')
        # for i, c in enumerate(db_chunks):
        #     print(i, hex(id(c)), c.id)

        # async with SessionLocal() as db:
        #     db.add_all(db_chunks)
        #     # await db.flush()
        #     await db.commit()
        print(
            f"ingestion_worker chunks end/chunks= {chunks}"
        )
        if not chunks:
            raise ValueError(f"No chunks extracted from document {document_id}")

        # ---- Embed ----
        embedding_service = EmbeddingService()
        texts = [chunk.content for chunk in chunks]
        embeddings = await embedding_service.embed_batch(texts)

        logger.debug(
            "ingestion_debug",
            chunks=len(chunks),
            texts=len(texts),
        )

        logger.debug(
            "embedding_debug",
            embeddings=len(embeddings),
        )
        # ---- Index in Qdrant ----
        qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)
        vector_store = VectorStore(qdrant_client)
        await vector_store.ensure_collection()

        logger.debug(
            "DOCUMENT_CHUNKS",
            document=document_name,
            count=len(chunks),
        )
        for i, chunk in enumerate(chunks):
            logger.debug(
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
            original_filename=original_filename
        )
        SessionLocal = get_sessionmaker()
        async with SessionLocal.begin() as db:

            for chunk, point_id in zip(chunks, point_ids):
                db.add(
                    DocumentChunkModel(
                        document_id=document_id,
                        content=chunk.content,
                        page_number=chunk.page_number,
                        chunk_index=chunk.chunk_index,
                        token_count=len(chunk.content.split()),
                        qdrant_point_id=point_id,
                        chunk_metadata=chunk.metadata,
                    )
                )

        logger.debug(
            "QDRANT_UPSERT",
            document=document_name,
            chunks=len(chunks),
            points=len(point_ids),
        )
        await qdrant_client.close()
        # await AsyncSessionLocal.kw["bind"].dispose()
        logger.warning("STEP_A")
        # ---- Update DB ----
        # logger.warning(
        #     "ENGINE-A",
        #     engine=id(AsyncSessionLocal.kw["bind"])
        # )
        import asyncio

        logger.warning(
            "EVENT_LOOP",
            loop=id(asyncio.get_running_loop())
        )
        logger.warning("BEFORE_EXECUTE")
        SessionLocal = get_sessionmaker()
        async with SessionLocal() as db:
            logger.warning("STEP_A-1")
            logger.warning(
                "DB_SESSION",
                session=id(db),
            )

            logger.warning(
                "DB_BIND",
                bind=id(db.bind),
            )
            result = await db.execute(
                select(DocumentModel).where(
                    DocumentModel.id == uuid.UUID(document_id)
                )
            )
            logger.warning("STEP_A-2")
            doc = result.scalar_one_or_none()
            logger.warning("STEP_A-3")
            if doc:
                logger.warning("STEP_A-4")
                doc.status = "indexed"
                doc.chunk_count = len(chunks)
                doc.page_count = parsed_doc.total_pages
                doc.qdrant_collection = settings.qdrant_collection_name
                await db.commit()
                logger.warning("STEP_A-5")
        logger.warning("AFTER_EXECUTE")
        # ---- Metrics ----
        latency = time.monotonic() - start_time
        logger.warning("STEP_A-6")
        DOCUMENTS_INGESTED_TOTAL.labels(status="success", mime_type=mime_type).inc()
        logger.warning("STEP_A-7")
        INGESTION_CHUNKS_CREATED.observe(len(chunks))
        logger.warning("STEP_A-8")
        INGESTION_LATENCY_SECONDS.observe(latency)
        logger.warning("STEP_A-9")
        logger.debug(
            "ingestion_completed",
            document_id=document_id,
            chunks=len(chunks),
            pages=parsed_doc.total_pages,
            latency_s=round(latency, 2),
        )
        logger.debug(
            "DOCUMENT_CHUNKS",
            file=document_name,
            chunks=len(chunks)
        )
        res = {
            "document_id": document_id,
            "status": "indexed",
            "chunks": len(chunks),
            "pages": parsed_doc.total_pages,
            "latency_s": round(latency, 2),
        }

        return res

    except Exception as exc:
        logger.error("ingestion_failed", document_id=document_id, error=str(exc))

        # Update DB with error
        try:
            logger.warning("STEP_B-1")
            # logger.warning(
            #     "ENGINE-B",
            #     engine=id(AsyncSessionLocal.kw["bind"])
            # )
            SessionLocal = get_sessionmaker()
            async with SessionLocal() as db2:
                logger.warning("STEP_B-2")
                logger.warning(
                    "DB2_SESSION",
                    session=id(db2),
                )

                logger.warning(
                    "DB2_BIND",
                    bind=id(db2.bind),
                )
                result = await db2.execute(
                    select(DocumentModel).where(
                        DocumentModel.id == uuid.UUID(document_id)
                    )
                )
                logger.warning("STEP_B-2")
                doc = result.scalar_one_or_none()
                logger.warning("STEP_B-3")
                if doc:
                    doc.status = "failed"
                    doc.error_message = str(exc)[:500]
                    await db2.commit()
                    logger.warning("STEP_B-4")
        except Exception as e:
            logger.error(
                "ingestion_worker. ",
                error=str(e),
                error_type=type(e).__name__,
            )
            import traceback
            traceback.print_exc()
            raise
        logger.warning("STEP_C-1")
        DOCUMENTS_INGESTED_TOTAL.labels(status="error", mime_type=mime_type).inc()
        logger.warning("STEP_C-2")
        # Retry with exponential backoff
        raise task.retry(exc=exc, countdown=2 ** task.request.retries * 30)
