"""
Pydantic v2 domain models — request/response schemas and domain entities.
Strict validation, serialization aliases, and computed fields.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


# =============================================================================
# Enums
# =============================================================================


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AgentType(StrEnum):
    RETRIEVER = "retriever"
    RESEARCH = "research"
    SUMMARIZER = "summarizer"
    CITATION = "citation"
    MEMORY = "memory"


# =============================================================================
# Base
# =============================================================================


class DomainModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        populate_by_name=True,
    )


# =============================================================================
# Document Schemas
# =============================================================================


class DocumentChunk(DomainModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    page_number: int | None = None
    chunk_index: int
    token_count: int | None = None
    qdrant_point_id: str | None = None
    chunk_metadata: dict[str, Any] = Field(default_factory=dict)


class Document(DomainModel):
    id: uuid.UUID
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    status: DocumentStatus
    version: int = 1
    page_count: int | None = None
    chunk_count: int | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias="document_metadata",
    )
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[misc]
    @property
    def is_ready(self) -> bool:
        return self.status == DocumentStatus.INDEXED


class DocumentUploadResponse(DomainModel):
    document_id: uuid.UUID
    filename: str
    status: DocumentStatus
    task_id: str
    message: str = "Document queued for ingestion"


class DocumentListResponse(DomainModel):
    documents: list[Document]
    total: int
    page: int
    page_size: int


# =============================================================================
# Chat / Conversation Schemas
# =============================================================================


class Citation(DomainModel):
    document_id: uuid.UUID
    document_name: str
    page_number: int | None = None
    chunk_content: str
    relevance_score: float
    chunk_index: int


class Message(DomainModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    tokens_used: int | None = None
    latency_ms: float | None = None
    model: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime


class Conversation(DomainModel):
    id: uuid.UUID
    session_id: str
    title: str | None = None
    is_active: bool
    message_count: int
    total_tokens: int
    summary: str | None = None
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChatRequest(DomainModel):
    session_id: str | None = None
    message: str = Field(..., min_length=1, max_length=4000)
    stream: bool = False
    document_ids: list[uuid.UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(DomainModel):
    session_id: str
    message_id: uuid.UUID
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tokens_used: int | None = None
    latency_ms: float | None = None
    agent_trace: dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# RAG Pipeline Schemas
# =============================================================================


class RetrievedChunk(DomainModel):
    """A chunk returned by the vector retriever."""

    chunk_id: str
    document_id: str
    document_name: str
    content: str
    page_number: int | None = None
    score: float
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(DomainModel):
    query: str
    rewritten_query: str | None = None
    chunks: list[RetrievedChunk]
    total_retrieved: int
    retrieval_latency_ms: float


# =============================================================================
# Evaluation Schemas
# =============================================================================


class EvaluationRequest(DomainModel):
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str | None = None


class EvaluationResult(DomainModel):
    message_id: uuid.UUID | None = None
    answer_relevancy: float | None = None
    faithfulness: float | None = None
    context_precision: float | None = None
    context_recall: float | None = None
    hallucination_score: float | None = None

    @computed_field  # type: ignore[misc]
    @property
    def overall_score(self) -> float | None:
        scores = [
            s
            for s in [
                self.answer_relevancy,
                self.faithfulness,
                self.context_precision,
            ]
            if s is not None
        ]
        return sum(scores) / len(scores) if scores else None


# =============================================================================
# Health / Status
# =============================================================================


class ServiceHealth(DomainModel):
    service: str
    status: str  # healthy | degraded | unhealthy
    latency_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(DomainModel):
    status: str
    version: str
    services: list[ServiceHealth]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
