from unittest.mock import AsyncMock, MagicMock

import pytest

from langchain_core.messages import HumanMessage
from app.rag.query_rewriter import QueryRewriter
from app.agents.state import AgentState


def make_state(
    query: str,
    messages=None,
) -> AgentState:
    return AgentState(
        session_id="test-session",
        query=query,
        messages=messages or [],
    )

@pytest.mark.asyncio
async def test_rewrite_returns_empty_query_without_llm():
    llm = MagicMock()
    rewriter = QueryRewriter(llm)

    state = make_state(query="   ")

    result = await rewriter.rewrite(state)

    assert result == ""


@pytest.mark.asyncio
async def test_rewrite_skips_protected_query(monkeypatch):
    llm = MagicMock()

    monkeypatch.setattr(
        "app.rag.query_rewriter.PROTECTED_TERMS",
        ["invoice"],
    )

    rewriter = QueryRewriter(llm)
    state = make_state("What is the invoice amount?")

    result = await rewriter.rewrite(state)

    assert result == "What is the invoice amount?"
    llm.assert_not_called()

@pytest.mark.asyncio
async def test_rewrite_without_llm_applies_deterministic_expansion(monkeypatch):
    rewriter = QueryRewriter(None)

    monkeypatch.setattr(
        "app.rag.query_rewriter.REWRITE_MAP",
        {"invoice": ["bill", "document"]},
    )
    monkeypatch.setattr(
        "app.rag.query_rewriter.PROTECTED_TERMS",
        [],
    )

    state = make_state("Invoice INT-2024-555")

    result = await rewriter.rewrite(state)

    assert result == "invoice int-2024-555 bill document"


@pytest.mark.asyncio
async def test_rewrite_without_llm_returns_original_when_no_expansion():
    rewriter = QueryRewriter(None)

    state = make_state(query="some completely unrelated question")

    result = await rewriter.rewrite(state)

    assert result == "some completely unrelated question"


@pytest.mark.asyncio
async def test_rewrite_calls_llm(monkeypatch):
    llm = MagicMock()

    response = MagicMock()
    response.content = "rewritten query"

    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=response)

    template = MagicMock()
    template.__or__ = MagicMock(return_value=chain)

    monkeypatch.setattr(
        "app.rag.query_rewriter.QUERY_REWRITE_TEMPLATE",
        template,
    )
    monkeypatch.setattr(
        "app.rag.query_rewriter.PROTECTED_TERMS",
        [],
    )

    rewriter = QueryRewriter(llm)

    state = make_state("invoice amount")

    result = await rewriter.rewrite(state)

    assert result == "rewritten query"
    chain.ainvoke.assert_awaited_once()

@pytest.mark.asyncio
async def test_llm_rewrite_falls_back_to_original_for_empty_response(monkeypatch):
    llm = MagicMock()

    response = MagicMock()
    response.content = "   "

    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=response)

    template = MagicMock()
    template.__or__ = MagicMock(return_value=chain)

    monkeypatch.setattr(
        "app.rag.query_rewriter.QUERY_REWRITE_TEMPLATE",
        template,
    )
    monkeypatch.setattr(
        "app.rag.query_rewriter.PROTECTED_TERMS",
        [],
    )

    rewriter = QueryRewriter(llm)
    state = make_state("some question")

    result = await rewriter.rewrite(state)

    assert result == "some question"
    chain.ainvoke.assert_awaited_once()

@pytest.mark.asyncio
async def test_llm_rewrite_rejects_non_string_response(monkeypatch):
    llm = MagicMock()

    response = MagicMock()
    response.content = {"unexpected": "object"}

    chain = MagicMock()
    chain.ainvoke = AsyncMock(return_value=response)

    template = MagicMock()
    template.__or__ = MagicMock(return_value=chain)

    monkeypatch.setattr(
        "app.rag.query_rewriter.QUERY_REWRITE_TEMPLATE",
        template,
    )
    monkeypatch.setattr(
        "app.rag.query_rewriter.PROTECTED_TERMS",
        [],
    )

    rewriter = QueryRewriter(llm)
    state = make_state("some question")

    with pytest.raises(
        TypeError,
        match="Expected string response, got dict",
    ):
        await rewriter.rewrite(state)

    chain.ainvoke.assert_awaited_once()

def test_build_context_without_messages():
    state = make_state(query="hello")

    result = QueryRewriter._build_context(state)

    assert result == "No prior context"

def test_build_context_uses_last_four_messages_and_truncates():
    messages = [
        HumanMessage(content=f"message-{i}" * 100)
        for i in range(6)
    ]

    state = make_state(
        "hello",
        messages=messages,
    )

    result = QueryRewriter._build_context(state)

    assert result
    assert "message-5" in result
    assert "message-0" not in result
    assert len(result) <= 3000