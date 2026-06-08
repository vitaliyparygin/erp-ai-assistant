"""
LangGraph typed state models for the multi-agent orchestration graph.
All state transitions are fully typed and validated.
"""
import uuid
from typing import Annotated, Any
from operator import add

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.models.schemas import Citation, RetrievedChunk


# =============================================================================
# Agent State
# =============================================================================

class AgentState(BaseModel):
    """
    Immutable typed state object passed between LangGraph nodes.

    Uses Annotated fields to specify how state is merged when
    nodes run in parallel (e.g., add_messages for message history).
    """

    # -------------------------------------------------------------------------
    # Input context
    # -------------------------------------------------------------------------
    session_id: str
    query: str
    original_query: str = ""
    document_ids: list[str] = Field(default_factory=list)

    # -------------------------------------------------------------------------
    # Conversation memory
    # -------------------------------------------------------------------------
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    conversation_summary: str | None = None
    message_count: int = 0

    # -------------------------------------------------------------------------
    # Retrieval results
    # -------------------------------------------------------------------------
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    reranked_chunks: list[RetrievedChunk] = Field(default_factory=list)
    rewritten_query: str | None = None
    retrieval_latency_ms: float | None = None

    # -------------------------------------------------------------------------
    # Research / reasoning
    # -------------------------------------------------------------------------
    research_notes: Annotated[list[str], add] = Field(default_factory=list)
    intermediate_answers: Annotated[list[str], add] = Field(default_factory=list)
    context_str: str = ""

    # -------------------------------------------------------------------------
    # Final output
    # -------------------------------------------------------------------------
    final_answer: str | None = None
    citations: list[Citation] = Field(default_factory=list)
    answer_confidence: float | None = None

    # -------------------------------------------------------------------------
    # Execution metadata
    # -------------------------------------------------------------------------
    agent_trace: dict[str, Any] = Field(default_factory=dict)
    errors: Annotated[list[str], add] = Field(default_factory=list)
    retries: dict[str, int] = Field(default_factory=dict)
    total_tokens: int = 0
    execution_path: Annotated[list[str], add] = Field(default_factory=list)

    # -------------------------------------------------------------------------
    # Routing flags
    # -------------------------------------------------------------------------
    needs_research: bool = False
    has_sufficient_context: bool = False
    requires_clarification: bool = False

    class Config:
        arbitrary_types_allowed = True


class NodeResult(BaseModel):
    """Result returned by each graph node."""

    node_name: str
    success: bool = True
    state_updates: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    latency_ms: float | None = None
    tokens_used: int = 0

    @classmethod
    def success_result(
        cls,
        node_name: str,
        state_updates: dict[str, Any],
        latency_ms: float | None = None,
        tokens_used: int = 0,
    ) -> "NodeResult":
        return cls(
            node_name=node_name,
            success=True,
            state_updates=state_updates,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

    @classmethod
    def failure_result(cls, node_name: str, error: str) -> "NodeResult":
        return cls(node_name=node_name, success=False, error=error)