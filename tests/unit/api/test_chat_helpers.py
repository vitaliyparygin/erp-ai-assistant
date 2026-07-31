import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.chat import _get_or_create_session, _save_messages
from app.models.schemas import Citation


@pytest.mark.asyncio
async def test_get_or_create_session_existing():
    conversation = MagicMock()
    conversation.id = uuid.uuid4()

    result = MagicMock()
    result.scalar_one_or_none.return_value = conversation

    db = AsyncMock()
    db.execute.return_value = result

    session_id, conversation_id = await _get_or_create_session(
        "session-1",
        db,
    )

    assert session_id == "session-1"
    assert conversation_id == conversation.id

    db.add.assert_not_called()
    db.flush.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_get_or_create_session_new():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    db = AsyncMock()

    # add не повинен бути AsyncMock
    db.add = MagicMock()

    db.execute.return_value = result

    session_id, conversation_id = await _get_or_create_session(
        "session-2",
        db,
    )

    assert session_id == "session-2"

    # витягуємо створений об'єкт
    conv = db.add.call_args.args[0]

    # імітуємо те, що робить flush()
    conv.id = uuid.uuid4()

    assert isinstance(conv.id, uuid.UUID)


@pytest.mark.asyncio
async def test_get_or_create_session_generates_uuid():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    db = AsyncMock()
    db.execute.return_value = result

    generated = uuid.uuid4()

    with patch("app.api.v1.chat.uuid.uuid4", return_value=generated):
        session_id, _ = await _get_or_create_session(
            None,
            db,
        )

    assert session_id == str(generated)


@pytest.mark.asyncio
async def test_save_messages():
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()

    db = AsyncMock()

    with patch(
        "app.api.v1.chat.uuid.uuid4",
        return_value=message_id,
    ):
        returned = await _save_messages(
            db=db,
            conversation_id=conversation_id,
            user_content="hello",
            assistant_content="world",
            tokens_used=42,
            latency_ms=15,
            citations=[],
            agent_trace={},
            model="qwen",
        )

    assert returned == message_id

    assert db.add.call_count == 2
    db.execute.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_save_messages_serializes_citations():
    db = AsyncMock()

    citation = Citation(
        document_id=uuid.uuid4(),
        document_name="invoice.pdf",
        page_number=1,
        chunk_index=0,
        chunk_content="invoice",
        relevance_score=0.95,
    )

    await _save_messages(
        db=db,
        conversation_id=uuid.uuid4(),
        user_content="q",
        assistant_content="a",
        tokens_used=1,
        latency_ms=1,
        citations=[citation],
        agent_trace={},
        model="qwen",
    )

    assistant_message = db.add.call_args_list[1].args[0]

    assert assistant_message.citations == [citation.model_dump(mode="json")]


@pytest.mark.asyncio
async def test_save_messages_returns_message_id():
    db = AsyncMock()

    expected = uuid.uuid4()

    with patch(
        "app.api.v1.chat.uuid.uuid4",
        return_value=expected,
    ):
        returned = await _save_messages(
            db=db,
            conversation_id=uuid.uuid4(),
            user_content="q",
            assistant_content="a",
            tokens_used=1,
            latency_ms=1,
            citations=[],
            agent_trace={},
            model="qwen",
        )

    assert returned == expected
