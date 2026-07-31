"""
Domain-specific exceptions for the ERP AI Assistant.
All exceptions map to appropriate HTTP status codes in the API layer.
"""

from typing import Any


class ERPAssistantError(Exception):
    """Base exception for all application errors."""

    status_code = 400

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)


# -----------------------------------------------------------------------------
# Document / Ingestion Errors
# -----------------------------------------------------------------------------


class DocumentNotFoundError(ERPAssistantError):
    """Raised when a requested document does not exist."""


class DocumentIngestionError(ERPAssistantError):
    """Raised when PDF/document ingestion fails."""


class UnsupportedFileTypeError(ERPAssistantError):
    """Raised when the uploaded file type is not supported."""

    status_code = 415


class FileSizeLimitExceededError(ERPAssistantError):
    """Raised when the uploaded file exceeds the size limit."""

    status_code = 413


# -----------------------------------------------------------------------------
# Conversation / Memory Errors
# -----------------------------------------------------------------------------


class ConversationNotFoundError(ERPAssistantError):
    """Raised when a conversation session cannot be found."""


class SessionExpiredError(ERPAssistantError):
    """Raised when a conversation session has expired."""


# -----------------------------------------------------------------------------
# RAG / Retrieval Errors
# -----------------------------------------------------------------------------


class VectorStoreError(ERPAssistantError):
    """Raised when vector store operations fail."""


class EmbeddingError(ERPAssistantError):
    """Raised when embedding generation fails."""


class RetrievalError(ERPAssistantError):
    """Raised when document retrieval fails."""


class NoRelevantDocumentsError(ERPAssistantError):
    """Raised when no relevant documents are found for a query."""


# -----------------------------------------------------------------------------
# Agent / Orchestration Errors
# -----------------------------------------------------------------------------


class AgentError(ERPAssistantError):
    """Base error for agent execution failures."""


class AgentTimeoutError(AgentError):
    """Raised when an agent exceeds its timeout threshold."""


class AgentRetryExhaustedError(AgentError):
    """Raised when all retry attempts for an agent are exhausted."""


class GraphExecutionError(AgentError):
    """Raised when LangGraph execution fails."""


# -----------------------------------------------------------------------------
# External Service Errors
# -----------------------------------------------------------------------------


class LLMError(ERPAssistantError):
    """Raised when LLM API calls fail."""


class LLMRateLimitError(LLMError):
    """Raised when OpenAI rate limits are hit."""


class CacheError(ERPAssistantError):
    """Raised when Redis cache operations fail."""


# -----------------------------------------------------------------------------
# Auth Errors
# -----------------------------------------------------------------------------


class AuthenticationError(ERPAssistantError):
    """Raised when authentication fails."""


class AuthorizationError(ERPAssistantError):
    """Raised when the user lacks required permissions."""


class RateLimitError(ERPAssistantError):
    """Raised when the API rate limit is exceeded."""
