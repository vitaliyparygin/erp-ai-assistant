from app.agents.retriever import get_unique_docs
from app.models.schemas import RetrievedChunk
import pytest
from unittest.mock import AsyncMock
from tests.factories import make_state
from app.agents.retriever import RetrieverAgent
from tests.factories import make_chunk
from tests.unit.agents.test_retriever_helpers import stub_rewrite


@pytest.mark.asyncio
async def test_same_query_after_rewrite():

    retriever = AsyncMock()
    retriever.retrieve.return_value = []

    reranker = AsyncMock()

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=reranker,
    )

    agent._rewrite_query = AsyncMock(
        return_value=(
            "invoice",
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )
    )

    await agent(make_state(query="invoice"))

    # retriever.retrieve.assert_awaited_once_with(
    #     "invoice"
    # )
    assert retriever.retrieve.await_args.kwargs["query"] == "invoice"


@pytest.mark.asyncio
async def test_retriever_uses_rewritten_query():

    retriever = AsyncMock()
    retriever.retrieve.return_value = []

    reranker = AsyncMock()

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=reranker,
    )

    agent._rewrite_query = AsyncMock(
        return_value=(
            "invoice amount",
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )
    )

    await agent(make_state(query="How much do we owe?"))

    assert retriever.retrieve.await_args.kwargs["query"] == "invoice amount"


def test_context_multiple_chunks():

    chunks = [
        make_chunk(
            document_name="Invoice.pdf",
            content="Invoice",
        ),
        make_chunk(
            document_name="PO.pdf",
            content="Purchase",
        ),
    ]

    context = RetrieverAgent._format_context(chunks)

    assert "Invoice.pdf" in context
    assert "PO.pdf" in context


def test_context_without_page():

    chunk = make_chunk(
        page_number=None,
    )

    context = RetrieverAgent._format_context([chunk])

    assert "page" not in context.lower()


def test_duplicate_documents_removed():

    docs = [
        make_chunk(
            document_name="Invoice.pdf",
            chunk_index=0,
        ),
        make_chunk(
            document_name="Invoice.pdf",
            chunk_index=5,
        ),
        make_chunk(
            document_name="PO.pdf",
            chunk_index=1,
        ),
    ]

    unique = get_unique_docs(docs)

    assert len(unique) == 2


def test_context_is_truncated():

    chunk = make_chunk(
        content="A" * 30000,
    )

    context = RetrieverAgent._format_context([chunk])

    assert len(context) < 22000


@pytest.mark.asyncio
async def test_empty_rerank_result():

    retriever = AsyncMock()
    retriever.retrieve.return_value = [
        make_chunk(),
    ]

    reranker = AsyncMock()
    reranker.rerank.return_value = []

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=reranker,
    )

    stub_rewrite(agent)

    result = await agent(make_state())

    assert result["reranked_chunks"] == []


@pytest.mark.asyncio
async def test_empty_retrieval():

    retriever = AsyncMock()
    retriever.retrieve.return_value = []

    reranker = AsyncMock()

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=reranker,
    )

    stub_rewrite(agent)

    result = await agent(make_state())

    assert result["retrieved_chunks"] == []


# @pytest.mark.asyncio
# async def test_reranker_exception_propagates():
#
#     retriever = AsyncMock()
#     retriever.retrieve.return_value = []
#
#     reranker = AsyncMock()
#     reranker.rerank.side_effect = RuntimeError("rerank failed")
#
#     agent = RetrieverAgent(
#         llm=AsyncMock(),
#         retriever=retriever,
#         reranker=reranker,
#     )
#
#     with pytest.raises(RuntimeError, match="rerank failed"):
#         await agent(make_state())


@pytest.mark.asyncio
async def test_retriever_exception_propagates():

    retriever = AsyncMock()
    retriever.retrieve.side_effect = RuntimeError("Qdrant failed")

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=AsyncMock(),
    )
    stub_rewrite(agent)

    with pytest.raises(RuntimeError, match="Qdrant failed"):
        await agent(make_state())


@pytest.mark.asyncio
async def test_format_context():
    from app.models.schemas import RetrievedChunk

    chunk = RetrievedChunk(
        document_id="1",
        document_name="Invoice.pdf",
        page_number=2,
        chunk_index=0,
        content="Invoice text",
        score=0.95,
        chunk_id="chunk-1",
    )

    context = RetrieverAgent._format_context([chunk])

    assert "Invoice.pdf" in context
    assert "Invoice text" in context


@pytest.mark.asyncio
async def test_format_context_empty():
    assert RetrieverAgent._format_context([]) == ""


@pytest.mark.asyncio
async def test_analyze_context_invalid_json():
    llm = AsyncMock()

    agent = RetrieverAgent(
        llm=llm,
        retriever=AsyncMock(),
        reranker=AsyncMock(),
    )

    chain = AsyncMock()
    chain.ainvoke.return_value.content = "not json"

    agent._llm = AsyncMock()

    class FakePrompt:
        def __or__(self, other):
            return chain

    import app.agents.retriever as retriever_module

    retriever_module.RETRIEVAL_ANALYSIS_TEMPLATE = FakePrompt()

    result = await agent._analyze_context(
        "query",
        "context",
    )

    assert result == {
        "has_sufficient_context": True,
        "needs_research": False,
    }


@pytest.mark.asyncio
async def test_empty_retrieval_returns_empty_context():
    retriever = AsyncMock()
    reranker = AsyncMock()

    retriever.retrieve.return_value = []
    reranker.rerank.return_value = []

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=reranker,
    )
    stub_rewrite(agent, query="invoice")
    state = make_state(query="invoice")

    result = await agent(state)

    assert result["retrieved_chunks"] == []
    assert result["reranked_chunks"] == []
    assert result["context_str"] == ""


def chunk(doc, chunk_id):
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=f"00000000-0000-0000-0000-{chunk_id:012}",
        document_name=doc,
        content="text",
        page_number=1,
        score=0.9,
        chunk_index=0,
    )


def test_duplicate_chunks_removed():
    docs = [
        chunk("Invoice.pdf", "1"),
        chunk("Invoice.pdf", "1"),
    ]

    unique = get_unique_docs(docs)

    assert len(unique) == 1


def test_duplicate_document_keeps_last_chunk():
    docs = [
        RetrievedChunk(
            chunk_id="1",
            document_id="00000000-0000-0000-0000-000000000001",
            document_name="Invoice.pdf",
            content="page1",
            page_number=1,
            score=0.7,
            chunk_index=0,
        ),
        RetrievedChunk(
            chunk_id="2",
            document_id="00000000-0000-0000-0000-000000000002",
            document_name="Invoice.pdf",
            content="page2",
            page_number=2,
            score=0.9,
            chunk_index=1,
        ),
    ]

    unique = get_unique_docs(docs)

    assert len(unique) == 1
    assert unique["Invoice.pdf"].page_number == 2


def test_context_contains_all_sources():
    chunks = []

    for i in range(10):
        chunks.append(
            RetrievedChunk(
                chunk_id=str(i),
                document_id=f"00000000-0000-0000-0000-{i:012}",
                document_name=f"doc{i}.pdf",
                page_number=1,
                score=0.9,
                chunk_index=0,
                content="hello",
            )
        )

    context = RetrieverAgent._format_context(chunks)

    assert context.count("[Source") == 10
