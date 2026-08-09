from uuid import uuid4
from unittest.mock import AsyncMock
from app.agents.retriever import (
    requires_contract_disambiguation,
    get_unique_docs,
    build_contract_disambiguation,
)
from app.retrieval.contracts import (
    is_contract_query,
    has_contract_identifier,
    is_ambiguous_contract_query,
)
from app.models.schemas import RetrievedChunk
from rules.models import DocumentType


def chunk(
    doc: str,
    chunk_id: str = "1",
    *,
    chunk_index: int = 0,
    contract_number: str | None = None,
    document_type=DocumentType.CONTRACT,
):
    metadata = {
        "document_type": document_type,
    }

    if contract_number:
        metadata["contract_number"] = contract_number

    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=str(uuid4()),
        document_name=doc,
        content="contract",
        page_number=1,
        score=0.9,
        chunk_index=chunk_index,
        metadata=metadata,
    )


def stub_rewrite(agent, query="invoice"):
    agent._rewrite_query = AsyncMock(
        return_value=(
            query,
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        )
    )


def test_is_contract_query():
    assert is_contract_query("Show contract")
    assert is_contract_query("договір")

    assert not is_contract_query(DocumentType.INVOICE)


def test_has_contract_identifier():
    assert has_contract_identifier("Contract ABC-2024-1")
    assert has_contract_identifier("ABC-2025-99")

    assert not has_contract_identifier(DocumentType.CONTRACT)


def test_is_ambiguous_contract_query():
    assert is_ambiguous_contract_query("Show contract")

    assert not is_ambiguous_contract_query("Show contract ABC-2024-1")

    assert not is_ambiguous_contract_query("Show invoice")


def test_requires_contract_disambiguation():
    docs = [
        chunk("1.pdf"),
        chunk("2.pdf"),
    ]

    assert requires_contract_disambiguation(
        "Show contract",
        docs,
    )


def test_requires_contract_disambiguation_false():
    docs = [
        chunk("1.pdf"),
    ]

    assert not requires_contract_disambiguation(
        "Show contract",
        docs,
    )


def test_get_unique_docs():
    docs = [
        chunk("a.pdf", chunk_index=0),
        chunk("a.pdf", chunk_index=1),
        chunk("b.pdf"),
    ]

    result = get_unique_docs(docs)

    assert len(result) == 2
    assert "a.pdf" in result
    assert "b.pdf" in result


def test_build_contract_disambiguation():
    answer = build_contract_disambiguation(
        [
            {
                "document_name": "Contract1.pdf",
                "contract_number": "C-001",
                "valid_until": "2027-01-01",
            },
            {
                "document_name": "Contract2.pdf",
            },
        ]
    )

    assert "Contract1.pdf" in answer
    assert "Contract2.pdf" in answer
    assert "C-001" in answer
