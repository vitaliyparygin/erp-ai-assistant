import pytest
from app.ingestion.query_metadata import extract_query_metadata
from rules.models import DocumentType
from rules.document_type import detect_document_type
from unittest.mock import AsyncMock
from app.agents.retriever import RetrieverAgent
from tests.factories import make_state, make_chunk


@pytest.mark.asyncio
async def test_duplicate_docs_after_rerank():
    c1 = make_chunk(
        document_id="doc1",
        chunk_index=0,
    )

    c2 = make_chunk(
        document_id="doc1",
        chunk_index=0,
    )

    retriever = AsyncMock()
    retriever.retrieve.return_value = [c1, c2]

    reranker = AsyncMock()
    reranker.rerank.return_value = [c1, c2]

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
    agent._analyze_context = AsyncMock(return_value={})

    result = await agent(make_state())

    assert len(result["retrieved_chunks"]) == 1


@pytest.mark.asyncio
async def test_metadata_passed_to_retriever():

    retriever = AsyncMock()
    retriever.retrieve.return_value = []

    reranker = AsyncMock()
    reranker.rerank.return_value = []

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=retriever,
        reranker=reranker,
    )
    agent._rewrite_query = AsyncMock(
        return_value=(
            "invoice number INV-100",
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )
    )

    agent._analyze_context = AsyncMock(return_value={})

    await agent(make_state())

    kwargs = retriever.retrieve.await_args.kwargs

    assert kwargs["query_metadata"]["invoice_number"] == "inv-100"


def test_extract_contract_number():

    meta = extract_query_metadata("Contract C-001")

    assert meta["contract_number"] == "C-001"


def test_detect_contract():

    assert detect_document_type("Contract C-001") == "Contract"


def test_extract_contract_identifier():

    meta = extract_query_metadata("Contract C-001")

    assert meta["contract_number"] == "C-001"
    assert "document_type" in meta


def test_extract_invoice():

    meta = extract_query_metadata("invoice INV-2025-001")

    assert meta["document_type"] == DocumentType.INVOICE


def test_extract_po():

    meta = extract_query_metadata("PO-2025-001")

    assert meta["document_type"] == DocumentType.PURCHASE_ORDER


def test_extract_contract():

    meta = extract_query_metadata("Contract C-001")

    assert meta["document_type"] == DocumentType.CONTRACT


def test_unknown_document():

    meta = extract_query_metadata("What is today's weather?")

    assert meta == {}


def test_filename_priority():

    meta = extract_query_metadata("Invoice.pdf contract C-001")

    assert meta["document_type"] == DocumentType.INVOICE


def test_regex_priority():

    meta = extract_query_metadata("INV-2025-001")

    assert meta["document_type"] == DocumentType.INVOICE
