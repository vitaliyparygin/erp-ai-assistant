import pytest
from unittest.mock import AsyncMock
from tests.factories import make_state
from app.agents.retriever import RetrieverAgent


@pytest.mark.asyncio
async def test_query_rewrite():
    rewriter = AsyncMock()
    rewriter.rewrite.return_value = (
        "invoice amount",
        {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        },
    )

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=AsyncMock(),
        reranker=AsyncMock(),
    )

    agent._query_rewriter = rewriter

    state = make_state(query="How much do we owe?")

    rewritten, usage = await agent._rewrite_query(state)

    assert rewritten == "invoice amount"
    assert usage == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
