import pytest
from unittest.mock import AsyncMock

from app.api.v1.chat import get_agent_graph
from app.graph.builder import ERPAssistantGraph


@pytest.mark.asyncio
async def test_get_agent_graph():
    qdrant = AsyncMock()
    redis = AsyncMock()

    settings = AsyncMock()

    graph = await get_agent_graph(
        qdrant=qdrant,
        redis=redis,
        settings=settings,
    )

    assert isinstance(graph, ERPAssistantGraph)
    assert graph is not None
