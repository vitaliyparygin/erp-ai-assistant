"""
Conversation management API endpoints.
Retrieve session history, list conversations, and delete sessions.
"""

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.core.dependencies import DBSessionDep, RedisDep
from app.core.exceptions import ConversationNotFoundError
from app.core.logging import get_logger
from app.memory.redis_memory import RedisMemoryStore
from app.models.orm import ConversationModel, MessageModel
from app.models.schemas import Conversation, ConversationListItem

router = APIRouter()
logger = get_logger(__name__)


@router.get(
    "/",
    response_model=list[ConversationListItem],
    summary="List all conversations",
)
async def list_conversations(
    page: int = 1,
    page_size: int = 20,
    active_only: bool = False,
    *,
    db: DBSessionDep,
) -> list[ConversationListItem]:
    """Return paginated conversation sessions, newest first."""
    offset = (page - 1) * page_size

    query = (
        select(ConversationModel)
        .order_by(ConversationModel.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    if active_only:
        query = query.where(ConversationModel.is_active.is_(True))

    result = await db.execute(query)
    conversations = result.scalars().all()

    return [
        ConversationListItem.model_validate(c)
        for c in conversations
    ]


@router.get(
    "/{conversation_id}",
    response_model=Conversation,
    summary="Get conversation with full message history",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: DBSessionDep,
) -> Conversation:
    result = await db.execute(
        select(ConversationModel)
        .where(ConversationModel.id == conversation_id)
        .options(selectinload(ConversationModel.messages))
    )

    conv = result.scalar_one_or_none()

    if not conv:
        raise ConversationNotFoundError(
            f"Conversation {conversation_id} not found"
        )

    return Conversation.model_validate(conv)


@router.get(
    "/session/{session_id}",
    response_model=Conversation,
    summary="Get conversation by session ID",
)
async def get_conversation_by_session(
    session_id: str,
    db: DBSessionDep,
) -> Conversation:
    """Look up a conversation using its Redis session ID."""
    result = await db.execute(
        select(ConversationModel)
        .where(ConversationModel.session_id == session_id)
        .options(selectinload(ConversationModel.messages))
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise ConversationNotFoundError(f"Session '{session_id}' not found")

    return Conversation.model_validate(conv)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: DBSessionDep,
    redis: RedisDep,
) -> None:
    """Delete a conversation, its messages, and clear the Redis session."""
    result = await db.execute(
        select(ConversationModel).where(ConversationModel.id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

    # Clear Redis memory for this session
    memory = RedisMemoryStore(redis_client=redis)
    await memory.clear_history(conv.session_id)

    await db.execute(
        delete(MessageModel).where(MessageModel.conversation_id == conversation_id)
    )
    await db.delete(conv)
    await db.commit()

    logger.info("conversation_deleted", conversation_id=str(conversation_id))


@router.patch(
    "/{conversation_id}/archive",
    response_model=Conversation,
    summary="Archive a conversation",
)
async def archive_conversation(
    conversation_id: uuid.UUID,
    db: DBSessionDep,
) -> Conversation:
    """Mark a conversation as inactive without deleting it."""
    result = await db.execute(
        select(ConversationModel).where(ConversationModel.id == conversation_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise ConversationNotFoundError(f"Conversation {conversation_id} not found")

    conv.is_active = False
    await db.commit()
    await db.refresh(conv)

    return Conversation.model_validate(conv)
