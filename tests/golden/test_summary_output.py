import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from app.agents.summarize import SummarizerAgent
from tests.factories import make_state


@pytest.mark.asyncio
async def test_summary_matches_golden():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(content="Invoice total is $1500.")
    )

    agent = SummarizerAgent(AsyncMock())

    agent._build_chain = Mock(
        return_value=chain,
    )

    state = make_state(
        query="invoice amount",
        context_str="Invoice Total: $1500",
    )

    result = await agent(state)

    assert result["final_answer"] == "Invoice total is $1500."
