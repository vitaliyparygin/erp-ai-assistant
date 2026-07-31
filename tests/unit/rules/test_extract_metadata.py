from rules import extract_metadata
from rules.models import DocumentType


def test_extract_contract_metadata():
    result = extract_metadata(
        text="""
        Contract Number: C-100
        Valid Until: 2027-05-01
        """,
        document_type=DocumentType.CONTRACT,
    )

    assert result["contract_number"] == "C-100"
    assert result["valid_until"] == "2027-05-01"


def test_extract_invoice_metadata():
    result = extract_metadata(
        text="""
        Invoice Number: INV-100
        Total Due: 1000.00
        """,
        document_type=DocumentType.INVOICE,
    )

    assert result["invoice_number"] == "INV-100"


def test_unknown_document_type_returns_empty():
    assert (
        extract_metadata(
            "hello",
            document_type=None,
        )
        == {}
    )


def test_missing_fields_returns_empty_dict():
    assert (
        extract_metadata(
            DocumentType.CONTRACT,
            document_type=DocumentType.CONTRACT,
        )
        == {}
    )


def test_extract_only_matching_fields():
    result = extract_metadata(
        text="""
        Contract Number: C-100
        Random text
        """,
        document_type=DocumentType.CONTRACT,
    )

    assert result == {
        "contract_number": "C-100",
    }
