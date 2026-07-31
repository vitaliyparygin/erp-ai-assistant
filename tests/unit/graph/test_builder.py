from tests.factories import make_state
from app.graph.builder import should_summarize
from unittest.mock import AsyncMock
from app.agents.state import AgentState
import pytest
from unittest.mock import MagicMock
from app.graph.builder import ERPAssistantGraph


def test_build_graph():
    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    compiled = MagicMock()

    graph._build_graph = MagicMock(
        return_value=compiled,
    )

    assert graph.build_graph() is compiled


@pytest.mark.asyncio
async def test_stream():
    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    class DummyGraph:
        async def astream_events(self, *args, **kwargs):
            yield {"event": "a"}
            yield {"event": "b"}

    graph._graph = DummyGraph()

    events = []

    async for event in graph.stream(None):
        events.append(event)

    assert events == [
        {"event": "a"},
        {"event": "b"},
    ]


@pytest.mark.asyncio
async def test_run_exception():
    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()
    graph._graph.ainvoke.side_effect = RuntimeError("boom")

    state = AgentState(
        session_id="1",
        query="q",
        original_query="q",
    )

    with pytest.raises(RuntimeError):
        await graph.run(state)


@pytest.mark.asyncio
async def test_run_returns_state():
    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.return_value = {
        "session_id": "1",
        "query": "hello",
        "original_query": "hello",
        "retrieved_chunks": [],
        "citations": [],
        "execution_path": [],
        "agent_trace": {},
    }

    state = AgentState(
        session_id="1",
        query="hello",
        original_query="hello",
    )

    result = await graph.run(state)

    assert isinstance(result, AgentState)


@pytest.mark.asyncio
async def test_invoke(monkeypatch):
    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()
    graph._graph.ainvoke.return_value = {
        "final_answer": "answer",
    }

    result = await graph.invoke(
        "hello",
        "session",
    )

    assert result["final_answer"] == "answer"

    graph._graph.ainvoke.assert_awaited_once()


def test_route_after_retrieval_summarizer():
    state = make_state()

    assert ERPAssistantGraph._route_after_retrieval(state) == "summarizer"


def test_route_after_retrieval_research():
    state = make_state(
        needs_research=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "research"


def test_route_after_retrieval_clarification():
    state = make_state(
        requires_clarification=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "end"


def test_should_summarize_true():
    state = make_state()

    assert should_summarize(state) is True


def test_should_summarize_false():
    state = make_state(
        disambiguated=True,
    )

    assert should_summarize(state) is False


def test_route_to_end():
    assert (
        ERPAssistantGraph._route_after_retrieval(
            make_state(
                requires_clarification=True,
            )
        )
        == "end"
    )


def test_route_to_research():
    assert (
        ERPAssistantGraph._route_after_retrieval(
            make_state(
                needs_research=True,
            )
        )
        == "research"
    )


def test_route_to_summarizer():
    assert (
        ERPAssistantGraph._route_after_retrieval(
            make_state(),
        )
        == "summarizer"
    )
