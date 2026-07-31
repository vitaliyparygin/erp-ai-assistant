"""
Document management API endpoints.
Handles uploads, ingestion status, listing, and deletion.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select

from app.core.dependencies import DBSessionDep, RateLimitDep, SettingsDep
from app.core.exceptions import (
    DocumentNotFoundError,
    FileSizeLimitExceededError,
    UnsupportedFileTypeError,
)
from app.core.logging import get_logger
from app.models.orm import DocumentModel
from app.models.schemas import (
    Document,
    DocumentListResponse,
    DocumentStatus,
    DocumentUploadResponse,
)

router = APIRouter()
logger = get_logger(__name__)

MIME_TYPE_MAP = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "md": "text/markdown",
}


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document for ingestion",
)
async def upload_document(
    file: UploadFile = File(...),
    tags: str = Form(default=""),
    *,
    db: DBSessionDep,
    settings: SettingsDep,
    _rate_limit: None = RateLimitDep,
) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required")

    extension = Path(file.filename).suffix.lstrip(".").lower()

    if extension not in settings.allowed_extensions:
        raise UnsupportedFileTypeError(
            f"File type '{extension}' not supported. Allowed: {settings.allowed_extensions}"
        )

    document_id = uuid.uuid4()

    content = await file.read()

    if len(content) > settings.max_upload_size_bytes:
        raise FileSizeLimitExceededError(
            f"File {len(content) / 1024 / 1024:.1f}MB exceeds "
            f"limit of {settings.max_upload_size_mb}MB"
        )

    mime_type = MIME_TYPE_MAP.get(extension, "application/octet-stream")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_filename = f"{document_id}.{extension}"
    file_path = upload_dir / safe_filename
    file_path.write_bytes(content)

    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

    doc = DocumentModel(
        id=document_id,
        filename=safe_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=mime_type,
        status=DocumentStatus.PENDING,
        tags=tag_list,
    )

    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    from app.workers.celery_app import celery_app

    task = celery_app.send_task(
        "ingest_document",
        kwargs={
            "document_id": str(document_id),
            "file_path": str(file_path),
            "mime_type": mime_type,
            "document_name": file.filename,
            "original_filename": file.filename,
        },
    )

    doc.document_metadata = {
        **(doc.document_metadata or {}),
        "celery_task_id": task.id,
    }

    await db.commit()

    logger.info(
        "document_upload_accepted",
        document_id=str(document_id),
        filename=file.filename,
        size_kb=round(len(content) / 1024, 1),
        task_id=task.id,
    )

    return DocumentUploadResponse(
        document_id=document_id,
        filename=file.filename,
        status=DocumentStatus.PENDING,
        task_id=task.id,
    )


@router.get("/", response_model=DocumentListResponse, summary="List documents")
async def list_documents(
    page: int = 1,
    page_size: int = 20,
    doc_status: DocumentStatus | None = None,
    *,
    db: DBSessionDep,
) -> DocumentListResponse:
    offset = (page - 1) * page_size
    query = select(DocumentModel).order_by(DocumentModel.created_at.desc())
    count_query = select(func.count(DocumentModel.id))

    if doc_status:
        query = query.where(DocumentModel.status == doc_status)
        count_query = count_query.where(DocumentModel.status == doc_status)

    results = await db.execute(query.offset(offset).limit(page_size))
    total = (await db.execute(count_query)).scalar() or 0

    return DocumentListResponse(
        documents=[Document.model_validate(d) for d in results.scalars().all()],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=Document, summary="Get document details")
async def get_document(document_id: uuid.UUID, db: DBSessionDep) -> Document:
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise DocumentNotFoundError(f"Document {document_id} not found")
    return Document.model_validate(doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    *,
    db: DBSessionDep,
    settings: SettingsDep,
) -> None:
    result = await db.execute(
        select(DocumentModel).where(DocumentModel.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise DocumentNotFoundError(f"Document {document_id} not found")

    try:
        from app.rag.retriever import VectorStore
        from qdrant_client import AsyncQdrantClient

        client = AsyncQdrantClient(url=settings.qdrant_url)
        await VectorStore(client).delete_document(str(document_id))
        await client.close()
    except Exception as e:
        logger.error("qdrant_delete_failed", error=str(e))

    Path(doc.file_path).unlink(missing_ok=True)
    await db.delete(doc)
    await db.commit()
    logger.info("document_deleted", document_id=str(document_id))
