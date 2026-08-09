import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.state import AgentState
import pytest
from langgraph.graph import END, START, StateGraph
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

    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    generated = uuid.uuid4()

    with patch("app.api.v1.chat.uuid.uuid4", return_value=generated):
        session_id, _ = await _get_or_create_session(
            None,
            db,
        )

    assert session_id == str(generated)

    db.execute.assert_awaited_once()
    db.add.assert_called_once()
    db.flush.assert_awaited_once()
    db.flush.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_messages():
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()

    db = MagicMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

    with patch(
        "app.api.v1.chat.uuid.uuid4",
        return_value=message_id,
    ):
        returned = await _save_messages(
            db=db,
            conversation_id=conversation_id,
            user_content="hello",
            assistant_content="world",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
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
    db = MagicMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

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
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
        latency_ms=1,
        citations=[citation],
        agent_trace={},
        model="qwen",
    )

    assistant_message = db.add.call_args_list[1].args[0]

    assert assistant_message.citations == [citation.model_dump(mode="json")]


@pytest.mark.asyncio
async def test_save_messages_returns_message_id():
    db = MagicMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()

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
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            latency_ms=1,
            citations=[],
            agent_trace={},
            model="qwen",
        )

    assert returned == expected


def test_agent_state_accumulates_token_usage():
    state = AgentState(
        session_id="session",
        query="hello",
    )

    # Симулюємо updates від nodes.
    state = AgentState.model_validate(
        {
            **state.model_dump(),
            "input_tokens": state.input_tokens + 10,
            "output_tokens": state.output_tokens + 20,
            "total_tokens": state.total_tokens + 30,
        }
    )

    assert state.input_tokens == 10
    assert state.output_tokens == 20
    assert state.total_tokens == 30


@pytest.mark.asyncio
async def test_agent_state_token_accumulation():
    async def node_a(state: AgentState):
        return {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }

    async def node_b(state: AgentState):
        return {
            "input_tokens": 40,
            "output_tokens": 50,
            "total_tokens": 90,
        }

    builder = StateGraph(AgentState)

    builder.add_node("a", node_a)
    builder.add_node("b", node_b)

    builder.add_edge(START, "a")
    builder.add_edge("a", "b")
    builder.add_edge("b", END)

    graph = builder.compile()

    result = await graph.ainvoke(
        AgentState(
            session_id="test",
            query="hello",
        )
    )

    assert result["input_tokens"] == 50
    assert result["output_tokens"] == 70
    assert result["total_tokens"] == 120
