from unittest.mock import AsyncMock

import pytest

from app.graph.builder import ERPAssistantGraph
from tests.factories import make_state


@pytest.mark.asyncio
async def test_graph_retriever_to_summarizer():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.return_value = {
        **make_state().model_dump(),
        "execution_path": [
            "memory",
            "retriever",
            "summarizer",
        ],
        "final_answer": "Invoice found",
    }

    result = await graph.run(make_state())

    assert result.final_answer == "Invoice found"

    assert result.execution_path == [
        "memory",
        "retriever",
        "summarizer",
    ]


@pytest.mark.asyncio
async def test_graph_research_path():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.return_value = {
        **make_state().model_dump(),
        "execution_path": [
            "memory",
            "retriever",
            "research",
            "summarizer",
        ],
        "research_notes": [
            "extra context",
        ],
        "final_answer": "answer",
    }

    result = await graph.run(make_state())

    assert "research" in result.execution_path

    assert result.research_notes == [
        "extra context",
    ]


@pytest.mark.asyncio
async def test_graph_stops_after_clarification():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.return_value = {
        **make_state().model_dump(),
        "requires_clarification": True,
        "final_answer": "Which contract?",
        "execution_path": [
            "memory",
            "retriever",
        ],
    }

    result = await graph.run(make_state())

    assert result.requires_clarification

    assert result.final_answer == "Which contract?"

    assert result.execution_path == [
        "memory",
        "retriever",
    ]


@pytest.mark.asyncio
async def test_graph_propagates_exception():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await graph.run(make_state())


@pytest.mark.asyncio
async def test_invoke_builds_initial_state():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.return_value = {}

    await graph.invoke(
        "hello",
        session_id="abc",
    )

    state = graph._graph.ainvoke.call_args.args[0]

    assert state.query == "hello"

    assert state.original_query == "hello"

    assert state.session_id == "abc"

    assert state.retrieved_chunks == []

    assert state.citations == []
