import pytest
from app.utils.resources import load_json
from app.ingestion.query_metadata import extract_query_metadata
from unittest.mock import patch
from app.retrieval.contracts import (
    normalize_document_type,
    build_contract_disambiguation,
    get_unique_docs,
)
from app.models.schemas import RetrievedChunk


def make_chunk(
    *,
    document_name: str,
    content: str,
    score: float,
    chunk_index: int = 0,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"chunk-{chunk_index}",
        document_id="document-1",
        document_name=document_name,
        content=content,
        score=score,
        chunk_index=chunk_index,
    )


def test_load_json_adds_json_extension():
    result = load_json("rewrite_map")

    assert isinstance(result, dict)


def test_load_json_accepts_json_extension():
    result = load_json("rewrite_map.json")

    assert isinstance(result, dict)


def test_load_json_missing_dictionary():
    with pytest.raises(FileNotFoundError, match="Dictionary"):
        load_json("__definitely_missing_dictionary__")


def test_extract_query_metadata_empty_question():
    result = extract_query_metadata("   ")

    assert result == {}


def test_extract_query_metadata_extracts_field():
    result = extract_query_metadata("What is the invoice number INV-2024-555?")

    assert "invoice_number" in result


def test_extract_query_metadata_extracts_person_name():
    result = extract_query_metadata("What did John Smith approve?")

    assert result["person"] == "John Smith"


def test_extract_query_metadata_extracts_document_type():
    with patch(
        "app.ingestion.query_metadata.detect_document_type",
        return_value="invoice",
    ):
        result = extract_query_metadata("What is the invoice amount?")

    assert result["document_type"] == "invoice"


def test_normalize_document_type_none():
    assert normalize_document_type(None) == ""


def test_normalize_document_type_value():
    assert normalize_document_type(" CONTRACT ") == " contract "


def test_build_contract_disambiguation_empty():
    assert build_contract_disambiguation([]) is None


def test_build_contract_disambiguation_contains_contract_details():
    contracts = [
        {
            "document_name": "Contract A.pdf",
            "contract_number": "CNT-001",
            "valid_until": "2026-12-31",
        }
    ]

    result = build_contract_disambiguation(contracts)

    assert result is not None
    assert "Contract A.pdf" in result
    assert "CNT-001" in result
    assert "2026-12-31" in result
    assert "Specify what you are talking about." in result


def test_build_contract_disambiguation_without_optional_fields():
    contracts = [
        {
            "document_name": "Contract A.pdf",
        }
    ]

    result = build_contract_disambiguation(contracts)

    assert "Contract A.pdf" in result
    assert "Number:" not in result
    assert "Valid until:" not in result


def test_get_unique_docs_keeps_last_chunk_for_same_document():
    first = make_chunk(
        document_name="invoice.pdf",
        content="first",
        score=0.8,
        chunk_index=0,
    )

    second = make_chunk(
        document_name="invoice.pdf",
        content="second",
        score=0.9,
        chunk_index=1,
    )

    result = get_unique_docs([first, second])

    assert list(result) == ["invoice.pdf"]
    assert result["invoice.pdf"] is second


def test_get_unique_docs_keeps_different_documents():
    first = make_chunk(
        document_name="invoice.pdf",
        content="invoice",
        score=0.8,
        chunk_index=0,
    )

    second = make_chunk(
        document_name="contract.pdf",
        content="contract",
        score=0.7,
        chunk_index=0,
    )

    result = get_unique_docs([first, second])

    assert list(result) == [
        "invoice.pdf",
        "contract.pdf",
    ]
    assert result["invoice.pdf"] is first
    assert result["contract.pdf"] is second
