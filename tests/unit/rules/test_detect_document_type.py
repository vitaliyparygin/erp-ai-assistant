import pytest
from rules.models import DocumentType
from rules import detect_document_type


@pytest.mark.parametrize(
    ("text", "filename", "expected"),
    [
        ("Invoice Number: INV-001", "doc.pdf", DocumentType.INVOICE),
        ("Purchase Order", "doc.pdf", DocumentType.PURCHASE_ORDER),
        ("Service Agreement", "doc.pdf", DocumentType.CONTRACT),
        ("Opportunity Name: ERP Upgrade", "doc.pdf", DocumentType.CRM_OPPORTUNITY),
        ("Employee ID: 123", "doc.pdf", DocumentType.EMPLOYEE),
    ],
)
def test_detect_by_content(text, filename, expected):
    assert detect_document_type(text, filename) == expected


@pytest.mark.parametrize(
    ("text", "filename", "expected"),
    [
        ("random text", "invoice.pdf", DocumentType.INVOICE),
        ("random text", "purchase_order.pdf", DocumentType.PURCHASE_ORDER),
        ("random text", "vendor_profile.pdf", DocumentType.VENDOR_PROFILE),
        ("random text", "project_status.pdf", DocumentType.PROJECT),
    ],
)
def test_detect_by_filename(text, filename, expected):
    assert detect_document_type(text, filename) == expected


def test_filename_has_priority():
    assert (
        detect_document_type(
            text="Invoice Number: INV-001",
            filename="contract.pdf",
        )
        == DocumentType.CONTRACT
    )


def test_unknown_document():
    assert (
        detect_document_type(
            text="hello world",
            filename="notes.txt",
        )
        is None
    )
