import pytest
from app.agents.retriever import RetrieverAgent
from tests.factories import make_state
from unittest.mock import AsyncMock
from app.agents.retriever import get_unique_docs
from tests.factories import retrieved_chunk
from unittest.mock import patch
from app.ingestion.metadata_extractor import MetadataExtractor
from app.graph.builder import ERPAssistantGraph
from rules.models import DocumentType
from app.agents.retriever import (
    build_contract_disambiguation,
)


@pytest.mark.asyncio
async def test_query_rewrite_returns_llm_result():
    rewriter = AsyncMock()
    rewriter.rewrite.return_value = "invoice amount"

    agent = RetrieverAgent(
        llm=AsyncMock(),
        retriever=AsyncMock(),
        reranker=AsyncMock(),
    )

    agent._query_rewriter = rewriter

    state = make_state(query="How much do we owe?")

    rewritten = await agent._rewrite_query(state)

    assert rewritten == "invoice amount"


def test_contract_disambiguation_contains_all_contracts():
    answer = build_contract_disambiguation(
        [
            {
                "document_name": "Maintenance.pdf",
                "contract_number": "C-001",
            },
            {
                "document_name": "Support.pdf",
                "contract_number": "C-002",
            },
        ]
    )

    assert "Maintenance.pdf" in answer
    assert "Support.pdf" in answer
    assert "Specify" in answer


# @pytest.mark.asyncio
# async def test_low_scores_are_filtered():
#     retriever = AsyncMock()
#     reranker = AsyncMock()
#
#     retriever.retrieve.return_value = []
#
#     agent = RetrieverAgent(
#         llm=AsyncMock(),
#         retriever=retriever,
#         reranker=reranker,
#     )
#
#     state = make_state()
#
#     result = await agent(state)
#
#     assert result["reranked_chunks"] == []


def test_duplicate_documents_keep_last():
    docs = [
        retrieved_chunk(
            document_name="Invoice.pdf",
            content="old",
        ),
        retrieved_chunk(
            document_name="Invoice.pdf",
            content="new",
        ),
    ]

    unique = get_unique_docs(docs)

    assert len(unique) == 1
    assert unique["Invoice.pdf"].content == "new"


@patch("app.ingestion.metadata_extractor.detect_document_type")
def test_filename_priority(mock_detect):
    mock_detect.return_value = DocumentType.INVOICE

    metadata = MetadataExtractor.extract(
        "Employment contract",
        "invoice.pdf",
    )

    assert metadata["document_type"] == DocumentType.INVOICE


def test_first_regex_wins():
    metadata = MetadataExtractor.extract(
        """
Invoice Number: INV-001
Invoice Number: INV-002
""",
        "invoice.pdf",
    )

    assert metadata["invoice_number"] == "INV-001"


@patch("app.ingestion.metadata_extractor.detect_document_type")
def test_unknown_document(mock_detect):
    mock_detect.return_value = None

    metadata = MetadataExtractor.extract(
        "random text",
        "abc.txt",
    )

    assert "document_type" not in metadata


def test_research_has_priority():
    state = make_state(
        needs_research=True,
        requires_clarification=False,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "research"


def test_empty_retrieval_goes_to_summary():
    state = make_state(
        reranked_chunks=[],
        needs_research=False,
        requires_clarification=False,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "summarizer"


def test_clarification_has_highest_priority():
    state = make_state(
        requires_clarification=True,
        needs_research=True,
    )

    assert ERPAssistantGraph._route_after_retrieval(state) == "end"
