"""Tests for rag_benchmark.classifier."""

from __future__ import annotations

from pathlib import Path

from rag_benchmark.classifier import UNKNOWN_TYPE, DefaultClassifier
from rag_benchmark.models import Document, DocumentFormat


def _doc(filename: str, text: str) -> Document:
    return Document(
        id="doc1",
        path=Path(filename),
        filename=filename,
        format=DocumentFormat.TXT,
        text=text,
        char_count=len(text),
    )


def test_classifies_invoice_by_content_and_filename() -> None:
    classifier = DefaultClassifier()
    doc = _doc(
        "invoice_001.txt",
        "Invoice Number: INV-1001\nTotal Due: $100.00\nBill To: Acme\n",
    )
    result = classifier.classify(doc)
    assert result.document_type == "Invoice"
    assert result.confidence > 0.5
    assert result.matched_signals


def test_classifies_vendor_profile() -> None:
    classifier = DefaultClassifier()
    doc = _doc("vendor.txt", "Vendor Name: Globex\nPhone: 555-0100\nEmail: a@b.com\n")
    result = classifier.classify(doc)
    assert result.document_type == "Vendor Profile"


def test_unclassifiable_document_returns_unknown() -> None:
    classifier = DefaultClassifier()
    doc = _doc("random.txt", "The quick brown fox jumps over the lazy dog.")
    result = classifier.classify(doc)
    assert result.document_type == UNKNOWN_TYPE
    assert result.confidence == 0.0


def test_filename_only_match_scores_lower_than_content_match() -> None:
    classifier = DefaultClassifier()
    filename_only = _doc("invoice_random.txt", "no relevant keywords here at all")
    content_only = _doc(
        "document.txt",
        "Invoice Number: INV-2\nTotal Due: $5.00\nBill To: Someone\n",
    )
    result_filename = classifier.classify(filename_only)
    result_content = classifier.classify(content_only)
    assert result_filename.document_type == "Invoice"
    assert result_content.document_type == "Invoice"
    assert result_content.confidence > result_filename.confidence
