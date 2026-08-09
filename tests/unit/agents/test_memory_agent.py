from langchain_core.messages import AIMessage, HumanMessage
import pytest
from unittest.mock import AsyncMock, Mock
from app.agents.memory import MemoryAgent
from tests.factories import make_state
from types import SimpleNamespace


@pytest.mark.asyncio
async def test_summary_not_generated_when_no_history():

    memory = AsyncMock()
    memory.get_history.return_value = []

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    result = await agent(make_state(session_id="abc"))

    assert result.get("conversation_summary") in (
        None,
        "",
    )


@pytest.mark.asyncio
async def test_summary_generated():

    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Conversation summary",
        )
    )

    memory = AsyncMock()

    memory.get_history.return_value = [
        HumanMessage(content="Question"),
        AIMessage(content="Answer"),
    ]

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    agent._settings.memory_summarization_threshold = 2

    agent._build_summary_chain = Mock(
        return_value=chain,
    )

    result = await agent(make_state(session_id="abc"))

    assert result["conversation_summary"] == "Conversation summary"
    assert result["input_tokens"] == 0
    assert result["output_tokens"] == 0
    assert result["total_tokens"] == 0


@pytest.mark.asyncio
async def test_summary_not_called_below_threshold():

    memory = AsyncMock()
    memory.get_history.return_value = [
        HumanMessage(content="1"),
        AIMessage(content="2"),
    ]

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    agent._summarize_history = AsyncMock()

    agent._settings.memory_summarization_threshold = 10

    await agent(make_state(session_id="abc"))

    agent._summarize_history.assert_not_awaited()


@pytest.mark.asyncio
async def test_summary_called_above_threshold():

    memory = AsyncMock()

    memory.get_history.return_value = [HumanMessage(content=str(i)) for i in range(20)]

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    agent._settings.memory_summarization_threshold = 5

    agent._summarize_history = AsyncMock(
        return_value=(
            "Summary",
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )
    )

    result = await agent(make_state(session_id="abc"))

    agent._summarize_history.assert_awaited_once()
    assert result["conversation_summary"] == "Summary"


@pytest.mark.asyncio
async def test_memory_exception():

    memory = AsyncMock()

    memory.get_history.side_effect = RuntimeError("redis failed")

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    with pytest.raises(
        RuntimeError,
        match="redis failed",
    ):
        await agent(make_state(session_id="abc"))


@pytest.mark.asyncio
async def test_history_is_truncated():

    history = [HumanMessage(content=f"q{i}") for i in range(30)]

    memory = AsyncMock()
    memory.get_history.return_value = history

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    result = await agent(make_state(session_id="abc"))

    assert len(result["messages"]) <= 20


# @pytest.mark.asyncio
# async def test_empty_history():
#
#     memory = AsyncMock()
#     memory.get_history.return_value = []
#
#     agent = MemoryAgent(
#         llm=AsyncMock(),
#         memory_store=memory,
#     )
#
#     result = await agent(
#         make_state(session_id="abc")
#     )
#
#     assert result["messages"] == []


@pytest.mark.asyncio
async def test_memory_loads_history():

    memory = AsyncMock()

    history = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi"),
    ]

    memory.get_history.return_value = history

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    result = await agent(make_state(session_id="abc"))

    memory.get_history.assert_awaited_once_with("abc")

    assert result["messages"] == history


@pytest.mark.asyncio
async def test_memory_loaded():

    memory = AsyncMock()

    memory.get_history.return_value = [
        HumanMessage(content="Hello"),
        AIMessage(content="Hi"),
    ]

    agent = MemoryAgent(
        llm=AsyncMock(),
        memory_store=memory,
    )

    result = await agent(make_state(session_id="123"))

    memory.get_history.assert_awaited_once_with("123")

    assert len(result["messages"]) == 2


@pytest.mark.asyncio
async def test_loads_history():
    llm = Mock()

    memory = Mock()
    memory.get_history = AsyncMock(
        return_value=[
            Mock(type="human", content="Hello"),
            Mock(type="ai", content="Hi"),
        ]
    )

    agent = MemoryAgent(llm, memory)

    result = await agent(make_state(session_id="session1"))

    assert result["messages"]
    assert result["message_count"] == 2
    assert result["execution_path"] == ["memory"]

    memory.get_history.assert_awaited_once_with("session1")


@pytest.mark.asyncio
async def test_empty_history():
    llm = Mock()

    memory = Mock()
    memory.get_history = AsyncMock(return_value=[])

    agent = MemoryAgent(llm, memory)

    result = await agent(make_state(session_id="session1"))

    assert result["messages"] == []
    assert result["message_count"] == 0


@pytest.mark.asyncio
async def test_memory_error():

    llm = Mock()

    memory = Mock()
    memory.get_history = AsyncMock(
        side_effect=RuntimeError("boom"),
    )

    agent = MemoryAgent(llm, memory)

    with pytest.raises(
        RuntimeError,
        match="boom",
    ):
        await agent(make_state(session_id="session1"))


@pytest.mark.asyncio
async def test_summarizes_long_history():
    llm = Mock()

    memory = Mock()
    memory.get_history = AsyncMock(
        return_value=[Mock(type="human", content=str(i)) for i in range(20)]
    )

    agent = MemoryAgent(llm, memory)

    agent._settings.memory_summarization_threshold = 3

    agent._summarize_history = AsyncMock(
        return_value=(
            "Summary",
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )
    )

    result = await agent(make_state(session_id="session1"))

    agent._summarize_history.assert_awaited_once()

    assert result["conversation_summary"] == "Summary"
    assert len(result["messages"]) == 4
