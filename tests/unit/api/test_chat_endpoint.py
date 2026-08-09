import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.chat import chat
from app.agents.state import AgentState
from app.models.schemas import ChatRequest


@pytest.mark.asyncio
async def test_chat_default_answer():
    graph = AsyncMock()

    state = AgentState(
        session_id="s",
        query="q",
        original_query="q",
    )

    state.final_answer = ""
    state.citations = []
    state.total_tokens = 0
    state.agent_trace = {}

    graph.run.return_value = state

    with (
        patch(
            "app.api.v1.chat.RedisMemoryStore",
            return_value=AsyncMock(),
        ),
        patch(
            "app.api.v1.chat._get_or_create_session",
            AsyncMock(return_value=("s", uuid.uuid4())),
        ),
        patch(
            "app.api.v1.chat._save_messages",
            AsyncMock(return_value=uuid.uuid4()),
        ),
    ):
        response = await chat(
            request=ChatRequest(message="q"),
            db=AsyncMock(),
            redis=AsyncMock(),
            settings=MagicMock(ollama_model="qwen"),
            graph=graph,
            qdrant=AsyncMock(),
            _rate_limit=None,
        )

    assert response.answer == ("I couldn't generate a response. Please try again.")


@pytest.mark.asyncio
async def test_chat_graph_exception():
    graph = AsyncMock()
    graph.run.side_effect = RuntimeError("boom")

    with (
        patch(
            "app.api.v1.chat._get_or_create_session",
            AsyncMock(return_value=("s", uuid.uuid4())),
        ),
        patch(
            "app.api.v1.chat.RedisMemoryStore",
            return_value=AsyncMock(),
        ),
    ):
        with pytest.raises(Exception) as exc:
            await chat(
                request=ChatRequest(message="hello"),
                db=AsyncMock(),
                redis=AsyncMock(),
                settings=MagicMock(),
                graph=graph,
                qdrant=AsyncMock(),
                _rate_limit=None,
            )

    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_chat_success():
    session_id = "session-1"
    conversation_id = uuid.uuid4()
    message_id = uuid.uuid4()

    graph = AsyncMock()

    result = AgentState(
        session_id=session_id,
        query="hello",
        original_query="hello",
        input_tokens=10,
        output_tokens=20,
        total_tokens=30,
    )
    result.final_answer = "Hi!"
    result.citations = []
    result.agent_trace = {}

    graph.run.return_value = result

    db = AsyncMock()

    redis = AsyncMock()

    settings = MagicMock()
    settings.app_version = "1.0"
    settings.ollama_model = "qwen"

    memory = AsyncMock()

    with (
        patch(
            "app.api.v1.chat.RedisMemoryStore",
            return_value=memory,
        ),
        patch(
            "app.api.v1.chat._get_or_create_session",
            AsyncMock(
                return_value=(session_id, conversation_id),
            ),
        ),
        patch(
            "app.api.v1.chat._save_messages",
            AsyncMock(return_value=message_id),
        ),
    ):
        response = await chat(
            request=ChatRequest(message="hello"),
            db=db,
            redis=redis,
            settings=settings,
            graph=graph,
            qdrant=AsyncMock(),
            _rate_limit=None,
        )

    assert response.answer == "Hi!"
    assert response.input_tokens == 10
    assert response.output_tokens == 20
    assert response.total_tokens == 30
    assert response.session_id == session_id
    assert response.message_id == message_id

    graph.run.assert_awaited_once()
    memory.add_user_message.assert_awaited_once()
    memory.add_ai_message.assert_awaited_once()
