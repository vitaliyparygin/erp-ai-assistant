from app.agents.state import AgentState
from rules.models import DocumentType
from app.models.schemas import RetrievedChunk
from langchain_core.messages import HumanMessage
from types import SimpleNamespace
from datetime import UTC, datetime
from uuid import uuid4
from app.models.orm import DocumentModel
from app.models.schemas import DocumentStatus


def make_settings(**overrides):
    defaults = {
        "app_version": "test",
        "upload_dir": "/tmp/uploads",
        "allowed_extensions": ["pdf", "docx", "txt", "md"],
        "max_upload_size_bytes": 10 * 1024 * 1024,
        "max_upload_size_mb": 10,
        "qdrant_url": "http://localhost:6333",
        "qdrant_collection_name": "documents",
        "ollama_base_url": "http://localhost:11434",
        "langfuse_enabled": False,
        "redis_url": "redis://localhost:6379/0",
        "database_url": "postgresql://...",
        "secret_key": "test",
        "rate_limit_enabled": False,
        "rate_limit_window": 60,
        "rate_limit_requests": 100,
    }

    defaults.update(overrides)

    return SimpleNamespace(**defaults)


def make_document(**kwargs) -> DocumentModel:
    now = datetime.now(UTC)

    data = dict(
        id=uuid4(),
        filename="123.pdf",
        original_filename="Invoice.pdf",
        file_path="/tmp/123.pdf",
        file_size=1024,
        mime_type="application/pdf",
        status=DocumentStatus.PENDING,
        tags=[],
        document_metadata={},
        created_at=now,
        updated_at=now,
        version=1,
        page_count=None,
        chunk_count=None,
        error_message=None,
        qdrant_collection=None,
    )

    data.update(kwargs)

    return DocumentModel(**data)


def make_conversation(**kwargs):
    data = dict(
        id=uuid4(),
        session_id="session-1",
        is_active=True,
        message_count=0,
        total_tokens=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        messages=[],
    )

    data.update(kwargs)

    return SimpleNamespace(**data)


def make_contract_chunk(
    *,
    document_name: str = "Maintenance.pdf",
    contract_number: str = "C-001",
    valid_until: str = "2027-01-01",
):
    return make_chunk(
        document_name=document_name,
        metadata={
            "document_type": "Contract",
            "contract_number": contract_number,
            "valid_until": valid_until,
        },
    )


def make_message(
    text: str = "Hello",
):
    return HumanMessage(content=text)


def make_chunk(
    *,
    chunk_id: str | None = None,
    document_id: str | None = None,
    document_name: str = "Invoice.pdf",
    content: str = "Invoice text",
    page_number: int | None = 1,
    score: float = 0.95,
    chunk_index: int = 0,
    metadata: dict | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id or str(uuid4()),
        document_id=document_id or str(uuid4()),
        document_name=document_name,
        content=content,
        page_number=page_number,
        score=score,
        chunk_index=chunk_index,
        metadata=metadata or {},
    )


def make_state(**kwargs):
    data = dict(
        session_id="test",
        query="q",
        original_query="q",
        messages=[],
        retrieved_chunks=[],
        reranked_chunks=[],
        research_notes=[],
        citations=[],
        final_answer=None,
    )

    data.update(kwargs)

    return AgentState(**data)


def retrieved_chunk(
    *,
    content: str = "text",
    document_name: str = "Invoice.pdf",
    document_type: DocumentType | str = DocumentType.INVOICE,
    score: float = 0.95,
    page_number: int = 1,
    chunk_index: int = 0,
    chunk_id: str | None = None,
    document_id: str | None = None,
    metadata: dict | None = None,
) -> RetrievedChunk:
    meta = {
        "document_type": document_type,
        "document_name": document_name,
    }

    if metadata:
        meta.update(metadata)

    return RetrievedChunk(
        chunk_id=chunk_id or str(uuid4()),
        document_id=document_id or str(uuid4()),
        document_name=document_name,
        content=content,
        page_number=page_number,
        score=score,
        chunk_index=chunk_index,
        metadata=meta,
    )
