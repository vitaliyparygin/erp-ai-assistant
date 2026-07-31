import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from tests.factories import make_state
from app.agents.retriever import RetrieverAgent


@pytest.mark.asyncio
async def test_query_rewrite():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="invoice amount",
        )
    )

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=AsyncMock(),
        reranker=AsyncMock(),
    )

    agent._build_rewrite_chain = Mock(
        return_value=chain,
    )

    state = make_state(query="How much do we owe?")

    rewritten = await agent._rewrite_query(state)

    assert rewritten == "invoice amount"
