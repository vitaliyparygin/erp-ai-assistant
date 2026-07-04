"""Tests for rag_benchmark.extractor."""

from __future__ import annotations

from pathlib import Path

from rag_benchmark.extractor import FieldRule, RegexMetadataExtractor
from rag_benchmark.models import Document, DocumentFormat


def _doc(text: str) -> Document:
    return Document(
        id="doc1",
        path=Path("doc.txt"),
        filename="doc.txt",
        format=DocumentFormat.TXT,
        text=text,
        char_count=len(text),
    )


def test_extracts_invoice_fields() -> None:
    extractor = RegexMetadataExtractor()
    doc = _doc(
        "Invoice Number: INV-1001\nBill To: Acme Corp\nTotal Due: $1,250.00\nCurrency: USD\n"
    )
    metadata = extractor.extract(doc, "Invoice")

    fields = metadata.as_plain_dict()
    assert fields["invoice_number"] == "INV-1001"
    assert fields["amount"] == "1,250.00"
    assert "Acme Corp" in fields["customer"]
    assert fields["currency"] == "USD"


def test_extracts_vendor_profile_fields() -> None:
    extractor = RegexMetadataExtractor()
    doc = _doc(
        "Vendor Name: Globex Industries\nPhone: +1-555-0100\n"
        "Email: contact@globex.example\nAddress: 42 Industrial Way\n"
    )
    metadata = extractor.extract(doc, "Vendor Profile")
    fields = metadata.as_plain_dict()

    assert "Globex" in fields["vendor"]
    assert fields["email"] == "contact@globex.example"
    assert "555-0100" in fields["phone"]


def test_unknown_document_type_yields_no_fields() -> None:
    extractor = RegexMetadataExtractor()
    doc = _doc("Some unrelated text.")
    metadata = extractor.extract(doc, "Nonexistent Type")
    assert metadata.fields == {}


def test_extra_rules_are_merged_and_take_priority_order() -> None:
    extra = {
        "Widget": (FieldRule("widget_id", (r"widget\s*id\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),),
    }
    extractor = RegexMetadataExtractor(extra_rules=extra)
    doc = _doc("Widget ID: W-42\n")
    metadata = extractor.extract(doc, "Widget")
    assert metadata.as_plain_dict()["widget_id"] == "W-42"


def test_missing_field_is_simply_omitted() -> None:
    extractor = RegexMetadataExtractor()
    doc = _doc("Invoice Number: INV-1\n")  # no amount, customer, currency
    metadata = extractor.extract(doc, "Invoice")
    fields = metadata.as_plain_dict()
    assert "invoice_number" in fields
    assert "amount" not in fields
