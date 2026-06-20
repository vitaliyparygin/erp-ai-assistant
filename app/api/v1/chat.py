"""
Chat API endpoints.
Supports both standard JSON responses and Server-Sent Events (SSE) streaming.
"""
import asyncio
import json
import time
import uuid
from uuid import uuid4
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.agents.state import AgentState
from app.core.config import get_settings, Settings
from app.core.dependencies import DBSessionDep, QdrantDep, RedisDep, RateLimitDep, SettingsDep
from app.core.logging import get_logger
from app.graph.builder import ERPAssistantGraph
from app.memory.redis_memory import RedisMemoryStore
from app.models.orm import ConversationModel, MessageModel
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    Citation,
    MessageRole,
)
from app.observability.metrics import GRAPH_EXECUTIONS_TOTAL, GRAPH_LATENCY_SECONDS
from app.rag.retriever import Reranker, VectorRetriever

from app.rag.embeddings import EmbeddingService
from app.rag.retriever import VectorRetriever
from app.services.llm_service import LLMService

from qdrant_client import AsyncQdrantClient
router = APIRouter()
logger = get_logger(__name__)
from sqlalchemy import select

# =============================================================================
# Dependency: build the agent graph per request
# =============================================================================

async def get_agent_graph(
    qdrant: QdrantDep,
    redis: RedisDep,
    settings: SettingsDep,
) -> ERPAssistantGraph:
    embedding_service = EmbeddingService(redis_client=redis)
    retriever = VectorRetriever(qdrant_client=qdrant, embedding_service=embedding_service)
    reranker = Reranker()
    memory_store = RedisMemoryStore(redis_client=redis)
    return ERPAssistantGraph(retriever=retriever, reranker=reranker, memory_store=memory_store)


# =============================================================================
# Helper: ensure/create conversation session
# =============================================================================

async def _get_or_create_session(
    session_id: str | None,
    db: AsyncSession,
) -> tuple[str, uuid.UUID]:
    """Return (session_id, conversation_db_id), creating a new record if needed."""


    new_session_id = session_id or str(uuid.uuid4())

    result = await db.execute(
        select(ConversationModel).where(
            ConversationModel.session_id == new_session_id
        )
    )
    conv = result.scalar_one_or_none()

    if conv is None:
        conv = ConversationModel(
            session_id=new_session_id,
            is_active=True,
        )
        db.add(conv)
        await db.flush()
        await db.commit()

    return new_session_id, conv.id


async def _save_messages(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_content: str,
    assistant_content: str,
    tokens_used: int,
    latency_ms: float,
    citations: list[Citation],
    agent_trace: dict,
    model: str,
) -> uuid.UUID:
    """Persist user + assistant messages and update conversation stats."""
    from sqlalchemy import select, update

    message_id = uuid.uuid4()

    user_msg = MessageModel(
        conversation_id=conversation_id,
        role=MessageRole.USER,
        content=user_content,
    )
    asst_msg = MessageModel(
        id=message_id,
        conversation_id=conversation_id,
        role=MessageRole.ASSISTANT,
        content=assistant_content,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        model=model,
        citations=[c.model_dump(mode="json") for c in citations],
        agent_trace=agent_trace,
    )

    db.add(user_msg)
    db.add(asst_msg)

    # Update conversation stats
    await db.execute(
        update(ConversationModel)
        .where(ConversationModel.id == conversation_id)
        .values(
            message_count=ConversationModel.message_count + 2,
            total_tokens=ConversationModel.total_tokens + tokens_used,
        )
    )

    await db.commit()
    return message_id


# =============================================================================
# Standard Chat Endpoint
# =============================================================================

@router.post(
    "/",
    response_model=ChatResponse,
)
async def chat(
    request: ChatRequest,
    *,
    db: DBSessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    graph: ERPAssistantGraph = Depends(get_agent_graph),
    _rate_limit: None = RateLimitDep,
    qdrant: QdrantDep,
) -> ChatResponse:

    logger.debug("CHAT ENDPOINT START")
    start_time = time.monotonic()

    session_id, conversation_id = await _get_or_create_session(request.session_id, db)
    memory_store = RedisMemoryStore(redis_client=redis)
    await memory_store.add_user_message(session_id, request.message)

    # Build initial state
    state = AgentState(
        session_id=session_id,
        query=request.message,
        original_query=request.message,
        document_ids=[str(d) for d in request.document_ids],
    )

    try:
        result_state = await graph.run(state)
        GRAPH_EXECUTIONS_TOTAL.labels(status="success").inc()
    except Exception as e:
        GRAPH_EXECUTIONS_TOTAL.labels(status="error").inc()
        logger.error("chat_graph_error", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {e}")

    latency_ms = round((time.monotonic() - start_time) * 1000, 2)
    GRAPH_LATENCY_SECONDS.observe(latency_ms / 1000)
    logger.debug(
        "RESULT_STATE_DEBUG",
        type=type(result_state).__name__,
        value=str(result_state)[:5000],
    )
    answer = result_state.final_answer or "I couldn't generate a response. Please try again."
    citations = result_state.citations or []
    tokens_used = result_state.total_tokens

    # Persist to memory and DB
    await memory_store.add_ai_message(session_id, answer)
    message_id = await _save_messages(
        db=db,
        conversation_id=conversation_id,
        user_content=request.message,
        assistant_content=answer,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        citations=citations,
        agent_trace=result_state.agent_trace,
        model=settings.ollama_model,
    )

    logger.debug(
        "chat_response_sent",
        session_id=session_id,
        latency_ms=latency_ms,
        tokens=tokens_used,
        citations=len(citations),
        path=result_state.execution_path,
    )

    return ChatResponse(
        session_id=str(session_id),
        message_id=str(message_id),
        answer=answer,
        citations=citations,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        agent_trace=result_state.agent_trace,
    )


# =============================================================================
# Streaming Chat Endpoint (SSE)
# =============================================================================

@router.get(
    "/stream",
    summary="Stream a chat response",
    description=(
        "Stream the agent response via Server-Sent Events (SSE). "
        "Connect with an EventSource and pass 'session_id' and 'message' query params."
    ),
)
async def chat_stream(
    request: Request,
    message: str,
    session_id: str | None = None,
    *,
    db: DBSessionDep,
    redis: RedisDep,
    settings: SettingsDep,
    graph: ERPAssistantGraph = Depends(get_agent_graph),
) -> EventSourceResponse:
    """SSE streaming endpoint for real-time response delivery."""
    resolved_session_id, conversation_id = await _get_or_create_session(session_id, db)
    memory_store = RedisMemoryStore(redis_client=redis)
    await memory_store.add_user_message(resolved_session_id, message)

    state = AgentState(
        session_id=resolved_session_id,
        query=message,
        original_query=message,
    )

    async def event_generator() -> AsyncGenerator[dict, None]:
        """Generate SSE events from the graph execution stream."""
        full_answer = ""
        start = time.monotonic()

        # Send connection acknowledgement
        yield {
            "event": "connected",
            "data": json.dumps({"session_id": resolved_session_id}),
        }

        try:
            async for event in graph.stream(state):
                event_name = event.get("event", "")
                event_data = event.get("data", {})

                # Stream agent status updates
                if event_name == "on_chain_start":
                    node = event_data.get("name", "")
                    if node in {"memory", "retriever", "research", "summarizer", "citation"}:
                        yield {
                            "event": "agent_start",
                            "data": json.dumps({"agent": node}),
                        }

                elif event_name == "on_chain_end":
                    node = event_data.get("name", "")
                    output = event_data.get("output", {})

                    if node == "summarizer" and output.get("final_answer"):
                        full_answer = output["final_answer"]
                        # Stream the answer in chunks
                        for i in range(0, len(full_answer), 20):
                            chunk = full_answer[i: i + 20]
                            yield {
                                "event": "token",
                                "data": json.dumps({"token": chunk}),
                            }
                            await asyncio.sleep(0.01)

                    if node in {"memory", "retriever", "research", "summarizer", "citation"}:
                        yield {
                            "event": "agent_end",
                            "data": json.dumps({"agent": node}),
                        }

            latency_ms = round((time.monotonic() - start) * 1000, 2)

            # Final event with metadata
            yield {
                "event": "done",
                "data": json.dumps({
                    "session_id": resolved_session_id,
                    "latency_ms": latency_ms,
                }),
            }

            # Persist to memory
            if full_answer:
                await memory_store.add_ai_message(resolved_session_id, full_answer)

        except asyncio.CancelledError:
            logger.error("stream_cancelled", session_id=resolved_session_id)
        except Exception as e:
            logger.error("stream_error", session_id=resolved_session_id, error=str(e))
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}),
            }

    return EventSourceResponse(event_generator())
