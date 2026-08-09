from tests.factories import make_state

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from app.agents.research import ResearchAgent


@pytest.mark.asyncio
async def test_research_passes_empty_conversation_context_without_messages():
    llm = MagicMock()

    agent = ResearchAgent(llm=llm)

    agent._chain = AsyncMock()
    agent._chain.ainvoke.return_value = SimpleNamespace(
        content="Research result",
        usage_metadata={},
    )

    state = make_state(
        query="What are the risks?",
        context_str="Retrieved context.",
        messages=[],
        research_notes=[],
        needs_research=True,
    )

    await agent(state)

    agent._chain.ainvoke.assert_awaited_once()

    prompt_input = agent._chain.ainvoke.await_args.args[0]

    assert prompt_input["conversation_context"] == ""


@pytest.mark.asyncio
async def test_research_passes_conversation_context():
    llm = MagicMock()

    agent = ResearchAgent(llm=llm)

    agent._chain = AsyncMock()
    agent._chain.ainvoke.return_value = SimpleNamespace(
        content="The main risk is project schedule slippage.",
        usage_metadata={
            "input_tokens": 10,
            "output_tokens": 8,
            "total_tokens": 18,
        },
    )

    state = make_state(
        query="What are the risks?",
        context_str="Project context from retrieved documents.",
        messages=[
            HumanMessage(content="What is the project status?"),
            HumanMessage(content="Tell me about the schedule."),
        ],
        research_notes=[],
        needs_research=True,
    )

    await agent(state)

    agent._chain.ainvoke.assert_awaited_once()

    prompt_input = agent._chain.ainvoke.await_args.args[0]

    assert prompt_input["query"] == "What are the risks?"
    assert prompt_input["context"] == ("Project context from retrieved documents.")
    assert prompt_input["research_notes"] == ""
    assert prompt_input["conversation_context"] == (
        "human: What is the project status?\n" "human: Tell me about the schedule."
    )


@pytest.mark.asyncio
async def test_query_sent_to_prompt():

    chain = AsyncMock()
    chain.ainvoke.return_value = SimpleNamespace(
        content="ERP",
    )

    agent = ResearchAgent(AsyncMock())
    agent._chain = chain

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

    chain = AsyncMock()
    chain.ainvoke.side_effect = RuntimeError("ollama failed")

    agent = ResearchAgent(AsyncMock())
    agent._chain = chain

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

    chain = AsyncMock()
    chain.ainvoke.return_value = SimpleNamespace(content="")

    agent = ResearchAgent(AsyncMock())
    agent._chain = chain

    result = await agent(
        make_state(
            needs_research=True,
        )
    )

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

    chain = AsyncMock()
    chain.ainvoke.return_value = SimpleNamespace(
        content="Research result",
    )

    agent = ResearchAgent(AsyncMock())
    agent._chain = chain

    result = await agent(
        make_state(
            query="invoice",
            context_str="context",
            needs_research=True,
        )
    )

    assert result["research_notes"] == ["Research result"]
