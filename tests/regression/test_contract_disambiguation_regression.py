import pytest
from app.retrieval.contracts import (
    requires_contract_disambiguation,
    has_contract_identifier,
)
from app.models.schemas import RetrievedChunk
from uuid import uuid4
from rules.models import DocumentType


def chunk(
    name: str,
    number: str,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=name,
        document_id=str(uuid4()),
        document_name=name,
        content="contract",
        page_number=1,
        score=0.9,
        chunk_index=0,
        metadata={
            "document_type": DocumentType.CONTRACT,
            "contract_number": number,
        },
    )


def test_contract_number_disables_disambiguation():
    chunks = [
        chunk("Maintenance.pdf", "C-001"),
        chunk("Support.pdf", "C-002"),
    ]

    assert (
        requires_contract_disambiguation(
            "Show contract C-001",
            chunks,
        )
        is False
    )


def test_multiple_contracts_require_disambiguation():
    chunks = [
        chunk("Maintenance.pdf", "C-001"),
        chunk("Support.pdf", "C-002"),
    ]

    assert (
        requires_contract_disambiguation(
            "Show contract",
            chunks,
        )
        is True
    )


def test_single_contract_does_not_require_disambiguation():
    chunks = [
        chunk("Maintenance.pdf", "C-001"),
    ]

    assert (
        requires_contract_disambiguation(
            "Show contract",
            chunks,
        )
        is False
    )


def test_non_contract_query():
    chunks = [
        chunk("Maintenance.pdf", "C-001"),
        chunk("Support.pdf", "C-002"),
    ]

    assert (
        requires_contract_disambiguation(
            "Show invoice",
            chunks,
        )
        is False
    )


@pytest.mark.parametrize(
    "query",
    [
        "Contract C-001",
        "contract c-001",
        "Maintenance contract C-001",
        "PO-2025-001",
        "INV-2026-15",
    ],
)
def test_has_contract_identifier(query):
    assert has_contract_identifier(query)


@pytest.mark.parametrize(
    "query",
    [
        "Show contract",
        "Maintenance contract",
        "Open agreement",
    ],
)
def test_has_contract_identifier_negative(query):
    assert not has_contract_identifier(query)
