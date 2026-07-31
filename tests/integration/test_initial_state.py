from unittest.mock import AsyncMock

import pytest

from app.graph.builder import ERPAssistantGraph


@pytest.mark.asyncio
async def test_invoke_builds_initial_state():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.return_value = {}

    await graph.invoke(
        "invoice",
        session_id="abc",
    )

    state = graph._graph.ainvoke.await_args.args[0]

    assert state.query == "invoice"

    assert state.original_query == "invoice"

    assert state.session_id == "abc"

    assert state.retrieved_chunks == []

    assert state.citations == []
