import pytest
from unittest.mock import AsyncMock
from rules.models import DocumentType
from app.agents.retriever import RetrieverAgent
from tests.factories import make_state
from app.graph.builder import ERPAssistantGraph
from app.ingestion.metadata_extractor import MetadataExtractor
from unittest.mock import patch
from app.models.schemas import RetrievedChunk


@pytest.mark.asyncio
async def test_empty_retrieval_returns_empty_chunks():
    retriever = AsyncMock()
    retriever.retrieve.return_value = []

    reranker = AsyncMock()

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=reranker,
    )

    result = await agent(make_state(query=DocumentType.INVOICE))

    assert result["retrieved_chunks"] == []


def test_route_to_clarification():
    state = make_state(
        requires_clarification=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "end"


def test_unknown_document():
    metadata = MetadataExtractor.extract(
        "some random text",
        "random.pdf",
    )

    assert "document_type" not in metadata


@patch("app.ingestion.metadata_extractor.detect_document_type")
def test_filename_priority(mock_detect):
    mock_detect.return_value = DocumentType.INVOICE

    metadata = MetadataExtractor.extract(
        "Contract Number C-001",
        "invoice.pdf",
    )

    assert metadata["document_type"] == DocumentType.INVOICE


def test_context_contains_source_header():
    chunk = RetrievedChunk(
        chunk_id="1",
        document_id="00000000-0000-0000-0000-000000000001",
        document_name="Invoice.pdf",
        content="Invoice total",
        page_number=4,
        score=0.95,
        chunk_index=0,
        metadata={},
    )

    context = RetrieverAgent._format_context([chunk])

    assert "[Source 1:" in context
    assert "Invoice.pdf" in context
    assert "Invoice total" in context
