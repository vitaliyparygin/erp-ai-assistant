from unittest.mock import Mock
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.agents.research import ResearchAgent
from tests.factories import make_state

# class FakeChain:
#     async def ainvoke(self, _):
#         return SimpleNamespace(
#             content="Research result",
#         )
#
#
# class FakePrompt:
#     def __or__(self, _):
#         return FakeChain()


@pytest.mark.asyncio
async def test_query_sent_to_prompt():

    chain = AsyncMock()
    chain.ainvoke.return_value = SimpleNamespace(
        content="ERP",
    )

    llm = AsyncMock()

    agent = ResearchAgent(llm)

    agent._build_chain = lambda: chain

    await agent(
        make_state(
            query="What is MRP?",
            needs_research=True,
        )
    )

    args = chain.ainvoke.await_args.args[0]

    assert args["query"] == "What is MRP?"


@pytest.mark.asyncio
async def test_llm_exception():

    llm = AsyncMock()
    llm.ainvoke.side_effect = RuntimeError("ollama failed")

    agent = ResearchAgent(llm)
    chain = Mock()
    chain.ainvoke = AsyncMock(
        side_effect=RuntimeError("ollama failed"),
    )

    agent._build_chain = Mock(
        return_value=chain,
    )

    with pytest.raises(
        RuntimeError,
        match="ollama failed",
    ):
        await agent(
            make_state(
                needs_research=True,
            )
        )


@pytest.mark.asyncio
async def test_latency_present():

    llm = AsyncMock()
    llm.ainvoke.return_value = SimpleNamespace(
        content="ERP",
    )

    result = await ResearchAgent(llm)(
        make_state(
            needs_research=True,
        )
    )

    assert result["agent_trace"]["research"]["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_execution_path():

    llm = AsyncMock()
    llm.ainvoke.return_value = SimpleNamespace(
        content="ERP",
    )

    agent = ResearchAgent(llm)

    result = await agent(
        make_state(
            needs_research=True,
        )
    )

    assert result["execution_path"] == [
        "research",
    ]


@pytest.mark.asyncio
async def test_empty_research_response():
    chain = Mock()
    chain.ainvoke = AsyncMock(return_value=SimpleNamespace(content=""))

    agent = ResearchAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    result = await agent(make_state())

    assert result["research_notes"] == [""]


# @pytest.mark.asyncio
# async def test_research_calls_llm():
#
#     llm = AsyncMock()
#     llm.ainvoke.return_value = SimpleNamespace(
#         content="Extra ERP knowledge",
#     )
#
#     agent = ResearchAgent(llm)
#
#     state = make_state(
#         query="How is depreciation calculated?",
#         needs_research=True,
#     )
#
#     result = await agent(state)
#
#     llm.ainvoke.assert_awaited_once()
#
#     assert result["research_notes"] == [
#         "Extra ERP knowledge",
#     ]


@pytest.mark.asyncio
async def test_research_skipped():
    agent = ResearchAgent(
        llm=AsyncMock(),
    )

    state = make_state(
        needs_research=False,
    )

    result = await agent(state)

    assert result["execution_path"] == ["research"]


@pytest.mark.asyncio
async def test_research_agent():

    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Research result",
        )
    )

    agent = ResearchAgent(
        llm=AsyncMock(),
    )

    agent._build_chain = Mock(
        return_value=chain,
    )

    state = make_state(
        query="invoice",
        context_str="context",
        needs_research=True,
    )

    result = await agent(state)

    assert result["research_notes"] == ["Research result"]
