from unittest.mock import AsyncMock

import pytest

from app.graph.builder import ERPAssistantGraph


@pytest.mark.asyncio
async def test_invoke_calls_graph():

    graph = ERPAssistantGraph.__new__(ERPAssistantGraph)

    graph._graph = AsyncMock()

    graph._graph.ainvoke.return_value = {
        "final_answer": "answer",
    }

    result = await graph.invoke(
        "hello",
        session_id="123",
    )

    graph._graph.ainvoke.assert_awaited_once()

    assert result["final_answer"] == "answer"
