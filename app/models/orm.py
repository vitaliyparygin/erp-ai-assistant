"""
SQLAlchemy ORM models.
All models use async-compatible patterns with UUID primary keys.
"""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    type_annotation_map = {
        dict[str, Any]: JSON,
    }


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# =============================================================================
# Document Models
# =============================================================================

class DocumentModel(Base, TimestampMixin):
    """Represents an uploaded business document."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending | processing | indexed | failed
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    document_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    qdrant_collection: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    chunks: Mapped[list["DocumentChunkModel"]] = relationship(
        "DocumentChunkModel", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename} status={self.status}>"


class DocumentChunkModel(Base, TimestampMixin):
    """Represents a text chunk extracted from a document."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    document: Mapped["DocumentModel"] = relationship("DocumentModel", back_populates="chunks")


# =============================================================================
# Conversation Models
# =============================================================================

class ConversationModel(Base, TimestampMixin):
    """Represents a chat session."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    conversations_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    messages: Mapped[list["MessageModel"]] = relationship(
        "MessageModel", back_populates="conversation", cascade="all, delete-orphan",
        order_by="MessageModel.created_at"
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} session={self.session_id}>"


class MessageModel(Base, TimestampMixin):
    """Represents a single message in a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    citations: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    agent_trace: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evaluation_scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    conversation: Mapped["ConversationModel"] = relationship(
        "ConversationModel", back_populates="messages"
    )


# =============================================================================
# Evaluation Model
# =============================================================================

class EvaluationModel(Base, TimestampMixin):
    """Stores RAGAS evaluation results for responses."""

    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    contexts: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    answer_relevancy: Mapped[float | None] = mapped_column(Float, nullable=True)
    faithfulness: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    context_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)