from tests.unit.agents.test_summary_helpers import FakePrompt
from langchain_core.messages import HumanMessage
from tests.factories import make_chunk
import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock
from unittest.mock import Mock
from app.agents.summarize import SummarizerAgent
from tests.factories import make_state


@pytest.mark.asyncio
async def test_llm_exception():

    chain = Mock()

    chain.ainvoke = AsyncMock(
        side_effect=RuntimeError("ollama"),
    )

    agent = SummarizerAgent(
        llm=AsyncMock(),
    )

    agent._build_chain = Mock(
        return_value=chain,
    )

    with pytest.raises(
        RuntimeError,
        match="ollama",
    ):
        await agent(make_state())


@pytest.mark.asyncio
async def test_empty_answer():

    chain = Mock()

    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="",
        )
    )

    agent = SummarizerAgent(
        llm=AsyncMock(),
    )

    agent._build_chain = Mock(
        return_value=chain,
    )

    result = await agent(make_state())

    assert result["final_answer"] == ""


@pytest.mark.asyncio
async def test_original_query_used():

    chain = Mock()

    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="ok",
        )
    )

    agent = SummarizerAgent(
        llm=AsyncMock(),
    )

    agent._build_chain = Mock(
        return_value=chain,
    )

    state = make_state(
        query="original",
        rewritten_query=None,
    )

    await agent(state)

    args = chain.ainvoke.await_args.args[0]

    assert args["query"] == "original"


@pytest.mark.asyncio
async def test_rewritten_query_used():

    chain = Mock()

    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="ok",
        )
    )

    agent = SummarizerAgent(
        llm=AsyncMock(),
    )

    agent._build_chain = Mock(
        return_value=chain,
    )

    state = make_state(
        rewritten_query="invoice amount",
    )

    await agent(state)

    args = chain.ainvoke.await_args.args[0]

    assert args["query"] == "invoice amount"


@pytest.mark.asyncio
async def test_summary_generated():

    chain = Mock()

    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Final answer",
        )
    )

    agent = SummarizerAgent(
        llm=AsyncMock(),
    )

    agent._build_chain = Mock(
        return_value=chain,
    )

    state = make_state(
        context_str="ERP context",
    )

    result = await agent(state)

    assert result["final_answer"] == "Final answer"


@pytest.mark.asyncio
async def test_llm_failure():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        side_effect=RuntimeError("Ollama failed"),
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    with pytest.raises(RuntimeError, match="Ollama failed"):
        await agent(make_state())


@pytest.mark.asyncio
async def test_total_tokens_saved():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Answer",
            usage_metadata={
                "total_tokens": 321,
            },
        )
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    result = await agent(make_state())

    assert result["total_tokens"] == 321


@pytest.mark.asyncio
async def test_citations_created():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Answer",
        )
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    state = make_state()

    state.reranked_chunks = [
        make_chunk(),
    ]

    result = await agent(state)

    assert len(result["citations"]) == 1


@pytest.mark.asyncio
async def test_last_six_messages_used():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Answer",
        )
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    state = make_state()

    state.messages = [HumanMessage(content=str(i)) for i in range(20)]

    await agent(state)

    args = chain.ainvoke.await_args.args[0]

    assert len(args["history"]) == 6


@pytest.mark.asyncio
async def test_history_is_sent():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Answer",
        )
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    state = make_state()

    state.messages = [
        HumanMessage(content="hello"),
    ]

    await agent(state)

    args = chain.ainvoke.await_args.args[0]

    assert len(args["history"]) == 1


@pytest.mark.asyncio
async def test_research_notes_are_used():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="Answer",
        )
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    state = make_state(
        research_notes=[
            "Wikipedia",
            "Vendor docs",
        ]
    )

    await agent(state)

    args = chain.ainvoke.await_args.args[0]

    assert "Wikipedia" in args["research_notes"]
    assert "Vendor docs" in args["research_notes"]


# @pytest.mark.asyncio
# async def test_llm_exception():
#     chain = Mock()
#     chain.ainvoke = AsyncMock(
#         side_effect=RuntimeError("boom")
#     )
#
#     agent = SummarizerAgent(AsyncMock())
#     agent._build_chain = Mock(return_value=chain)
#
#     with pytest.raises(RuntimeError):
#         await agent(
#             make_state(
#                 context_str="ctx"
#             )
#         )


@pytest.mark.asyncio
async def test_missing_usage_metadata():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="answer",
        )
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    result = await agent(make_state(context_str="ctx"))

    assert result["total_tokens"] == 0


@pytest.mark.asyncio
async def test_usage_metadata():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(
            content="answer",
            usage_metadata={
                "total_tokens": 321,
            },
        )
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    result = await agent(make_state(context_str="ctx"))

    assert result["total_tokens"] == 321


@pytest.mark.asyncio
async def test_history_passed():
    chain = Mock()
    chain.ainvoke = AsyncMock(return_value=SimpleNamespace(content="answer"))

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    history = [
        HumanMessage(
            type="human",
            content="hello",
        )
    ]

    state = make_state(
        messages=history,
        context_str="ctx",
    )

    await agent(state)

    payload = chain.ainvoke.await_args.args[0]

    assert payload["history"] == history


@pytest.mark.asyncio
async def test_research_notes_are_passed():
    chain = Mock()
    chain.ainvoke = AsyncMock(return_value=SimpleNamespace(content="answer"))

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    state = make_state(
        research_notes=[
            "note1",
            "note2",
        ],
        context_str="ctx",
    )

    await agent(state)

    payload = chain.ainvoke.await_args.args[0]

    assert payload["research_notes"] == "note1\nnote2"


@pytest.mark.asyncio
async def test_empty_context():
    chain = Mock()
    chain.ainvoke = AsyncMock(
        return_value=SimpleNamespace(content="I don't have enough information.")
    )

    agent = SummarizerAgent(AsyncMock())
    agent._build_chain = Mock(return_value=chain)

    state = make_state(
        query="invoice",
        context_str="",
    )

    result = await agent(state)

    assert result["final_answer"] == "I don't have enough information."


@pytest.mark.asyncio
async def test_summarizer(monkeypatch):
    monkeypatch.setattr(
        "app.agents.summarize.SUMMARIZER_TEMPLATE",
        FakePrompt(),
    )

    agent = SummarizerAgent(object())

    state = make_state(
        query="question",
        context_str="context",
        reranked_chunks=[],
        research_notes=[],
        messages=[],
    )

    result = await agent(state)

    assert result["final_answer"] == "Final answer"
