"""Tests for rag_benchmark.metrics."""

from __future__ import annotations

from pathlib import Path

from rag_benchmark.metrics import compute_statistics, validate_dataset
from rag_benchmark.models import (
    BenchmarkDataset,
    BenchmarkQuery,
    ClassificationResult,
    ClassifiedDocument,
    Difficulty,
    Document,
    DocumentFormat,
    ExtractedMetadata,
)


def _classified(doc_type: str, filename: str) -> ClassifiedDocument:
    document = Document(
        id=filename, path=Path(filename), filename=filename,
        format=DocumentFormat.TXT, text="x", char_count=1,
    )
    classification = ClassificationResult(document_id=filename, document_type=doc_type, confidence=0.5)
    metadata = ExtractedMetadata(document_id=filename, document_type=doc_type, fields={})
    return ClassifiedDocument(document=document, classification=classification, metadata=metadata)


def test_compute_statistics_counts_and_averages() -> None:
    documents = [_classified("Invoice", "a.txt"), _classified("Unknown", "b.txt")]
    dataset = BenchmarkDataset(
        queries=[
            BenchmarkQuery(
                id=1, query="q1", expected_document="a.txt", expected_fields=[],
                document_type="Invoice", difficulty=Difficulty.EASY,template_id="Invoice"
            )
        ]
    )
    stats = compute_statistics(documents, dataset)

    assert stats.total_documents == 2
    assert stats.total_questions == 1
    assert stats.unknown_document_types == 1
    assert stats.avg_questions_per_document == 0.5
    assert "1 document(s) could not be classified." in stats.warnings


def test_validate_dataset_detects_duplicate_ids() -> None:
    dataset = BenchmarkDataset(
        queries=[
            BenchmarkQuery(id=1, query="q1", expected_document="a.txt", document_type="Invoice", difficulty=Difficulty.EASY,template_id="Invoice"),
            BenchmarkQuery(id=1, query="q2", expected_document="a.txt", document_type="Invoice", difficulty=Difficulty.EASY,template_id="Invoice"),
        ]
    )
    report = validate_dataset(dataset)
    codes = {issue.code for issue in report.issues}
    assert "duplicate_id" in codes
    assert report.has_errors


def test_validate_dataset_detects_missing_expected_document() -> None:
    dataset = BenchmarkDataset(
        queries=[
            BenchmarkQuery(id=1, query="q1", expected_document="", document_type="Invoice", difficulty=Difficulty.EASY,template_id="Invoice"),
        ]
    )
    report = validate_dataset(dataset)
    codes = {issue.code for issue in report.issues}
    assert "missing_expected_document" in codes


def test_validate_dataset_detects_missing_extracted_fields() -> None:
    documents = [_classified("Invoice", "a.txt")]
    dataset = BenchmarkDataset(
        queries=[
            BenchmarkQuery(
                id=1, query="q1", expected_document="a.txt",
                expected_fields=["invoice_number"], document_type="Invoice",
                difficulty=Difficulty.EASY,template_id="Invoice"
            )
        ]
    )
    report = validate_dataset(dataset, classified_documents=documents)
    codes = {issue.code for issue in report.issues}
    assert "missing_extracted_fields" in codes


def test_validate_dataset_no_issues_on_clean_dataset() -> None:
    dataset = BenchmarkDataset(
        queries=[
            BenchmarkQuery(id=1, query="q1", expected_document="a.txt", document_type="Invoice", difficulty=Difficulty.EASY,template_id="Invoice"),
        ]
    )
    report = validate_dataset(dataset)
    assert report.issues == []
    assert not report.has_errors
