from types import SimpleNamespace
from uuid import uuid4
from app.models.schemas import Citation
from tests.factories import make_chunk
import pytest
from unittest.mock import AsyncMock
from app.agents.citation import CitationAgent
from tests.factories import make_state


def chunk(name):
    return SimpleNamespace(
        metadata={
            "document_name": name,
        }
    )


@pytest.mark.asyncio
async def test_citation_fields():

    chunk = make_chunk(
        document_name="Invoice.pdf",
        page_number=5,
        score=0.91,
    )

    agent = CitationAgent(llm=object())

    state = make_state(
        final_answer="answer",
        reranked_chunks=[chunk],
    )

    result = await agent(state)

    citation = result["citations"][0]

    assert citation.document_name == "Invoice.pdf"
    assert citation.page_number == 5
    assert citation.relevance_score == 0.91


@pytest.mark.asyncio
async def test_first_three_chunks_used():

    agent = CitationAgent(llm=object())

    state = make_state(
        final_answer="answer",
        reranked_chunks=[
            make_chunk(document_name="1.pdf"),
            make_chunk(document_name="2.pdf"),
            make_chunk(document_name="3.pdf"),
            make_chunk(document_name="4.pdf"),
        ],
    )

    result = await agent(state)

    assert len(result["citations"]) == 3


@pytest.mark.asyncio
async def test_chunk_preview():

    agent = CitationAgent(
        llm=AsyncMock(),
    )

    state = make_state(
        final_answer="answer",
        reranked_chunks=[
            make_chunk(
                content="A" * 1000,
            )
        ],
    )

    result = await agent(state)

    assert len(result["citations"][0].chunk_content) == 300


@pytest.mark.asyncio
async def test_max_three_citations():

    agent = CitationAgent(
        llm=AsyncMock(),
    )

    state = make_state(
        final_answer="answer",
        reranked_chunks=[make_chunk(document_name=f"{i}.pdf") for i in range(5)],
    )

    result = await agent(state)

    assert len(result["citations"]) == 3


@pytest.mark.asyncio
async def test_single_citation():

    agent = CitationAgent(
        llm=AsyncMock(),
    )

    state = make_state(
        final_answer="answer",
        reranked_chunks=[
            make_chunk(
                document_name="Invoice.pdf",
                page_number=7,
            )
        ],
    )

    result = await agent(state)

    assert len(result["citations"]) == 1

    citation = result["citations"][0]

    assert citation.document_name == "Invoice.pdf"
    assert citation.page_number == 7


@pytest.mark.asyncio
async def test_no_chunks():

    agent = CitationAgent(
        llm=AsyncMock(),
    )

    state = make_state(
        final_answer="answer",
        reranked_chunks=[],
    )

    result = await agent(state)

    assert result["citations"] == []


@pytest.mark.asyncio
async def test_no_answer():

    agent = CitationAgent(
        llm=AsyncMock(),
    )

    state = make_state(
        final_answer=None,
    )

    result = await agent(state)

    assert result["citations"] == []


@pytest.mark.asyncio
async def test_chunk_content_is_truncated():

    chunk = make_chunk(
        content="A" * 1000,
    )

    agent = CitationAgent(AsyncMock())

    result = await agent(
        make_state(
            final_answer="Answer",
            reranked_chunks=[chunk],
        )
    )

    citation = result["citations"][0]

    assert len(citation.chunk_content) == 300


@pytest.mark.asyncio
async def test_document_id_is_uuid():

    uid = uuid4()

    chunk = make_chunk(
        document_id=str(uid),
    )

    agent = CitationAgent(AsyncMock())

    result = await agent(
        make_state(
            final_answer="Answer",
            reranked_chunks=[chunk],
        )
    )

    citation = result["citations"][0]

    assert citation.document_id == uid


@pytest.mark.asyncio
async def test_only_first_three_chunks_used():

    chunks = [make_chunk(document_name=f"doc{i}.pdf") for i in range(5)]

    agent = CitationAgent(AsyncMock())

    result = await agent(
        make_state(
            final_answer="Answer",
            reranked_chunks=chunks,
        )
    )

    assert len(result["citations"]) == 3


@pytest.mark.asyncio
async def test_single_chunk_creates_single_citation():

    chunk = make_chunk()

    agent = CitationAgent(AsyncMock())

    result = await agent(
        make_state(
            final_answer="Answer",
            reranked_chunks=[chunk],
        )
    )

    citations = result["citations"]

    assert len(citations) == 1

    citation = citations[0]

    assert citation.document_name == chunk.document_name
    assert citation.page_number == chunk.page_number
    assert citation.chunk_index == chunk.chunk_index
    assert citation.relevance_score == chunk.score


@pytest.mark.asyncio
async def test_no_chunks_returns_no_citations():

    agent = CitationAgent(AsyncMock())

    result = await agent(
        make_state(
            final_answer="Answer",
            reranked_chunks=[],
        )
    )

    assert result["citations"] == []


@pytest.mark.asyncio
async def test_empty_answer_returns_no_citations():

    agent = CitationAgent(AsyncMock())

    result = await agent(
        make_state(
            final_answer="",
            reranked_chunks=[],
        )
    )

    assert result == {
        "citations": [],
        "execution_path": ["citation"],
    }


@pytest.mark.asyncio
async def test_empty_answer():
    agent = CitationAgent(object())

    state = make_state(
        final_answer=None,
        reranked_chunks=[],
    )

    result = await agent(state)

    assert result["citations"] == []


@pytest.mark.asyncio
async def test_no_answer_returns_empty():

    agent = CitationAgent(llm=None)

    state = make_state(
        final_answer=None,
        reranked_chunks=[
            make_chunk(),
        ],
    )

    result = await agent(state)

    assert result == {
        "citations": [],
        "execution_path": ["citation"],
    }


@pytest.mark.asyncio
async def test_no_chunks_returns_empty():

    agent = CitationAgent(llm=None)

    state = make_state(
        final_answer="Invoice is paid",
        reranked_chunks=[],
    )

    result = await agent(state)

    assert result == {
        "citations": [],
        "execution_path": ["citation"],
    }


@pytest.mark.asyncio
async def test_build_citations():

    agent = CitationAgent(llm=None)

    chunk = make_chunk(
        document_name="Invoice.pdf",
        page_number=3,
        score=0.95,
    )

    state = make_state(
        final_answer="Invoice paid",
        reranked_chunks=[chunk],
    )

    result = await agent(state)

    citations = result["citations"]

    assert len(citations) == 1

    citation = citations[0]

    assert isinstance(citation, Citation)

    assert citation.document_name == "Invoice.pdf"
    assert citation.page_number == 3
    assert citation.relevance_score == 0.95


@pytest.mark.asyncio
async def test_only_top_three():

    agent = CitationAgent(llm=None)

    state = make_state(
        final_answer="answer",
        reranked_chunks=[make_chunk(document_name=f"{i}.pdf") for i in range(5)],
    )

    result = await agent(state)

    assert len(result["citations"]) == 3


@pytest.mark.asyncio
async def test_document_id_converted_to_uuid():

    uid = str(uuid4())

    agent = CitationAgent(llm=None)

    chunk = make_chunk(
        document_id=uid,
    )

    result = await agent(
        make_state(
            final_answer="answer",
            reranked_chunks=[chunk],
        )
    )

    assert result["citations"][0].document_id == uuid4().__class__(uid)


@pytest.mark.asyncio
async def test_chunk_content_truncated():

    agent = CitationAgent(llm=None)

    chunk = make_chunk(
        content="A" * 1000,
    )

    result = await agent(
        make_state(
            final_answer="answer",
            reranked_chunks=[chunk],
        )
    )

    assert len(result["citations"][0].chunk_content) == 300


@pytest.mark.asyncio
async def test_empty_chunks():

    agent = CitationAgent(llm=object())

    state = make_state(
        final_answer="answer",
        reranked_chunks=[],
    )

    result = await agent(state)

    assert result["citations"] == []
