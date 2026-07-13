"""Tests for rag_benchmark.writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from rag_benchmark.models import (
    BenchmarkDataset,
    BenchmarkQuery,
    DatasetStatistics,
    Difficulty,
    LatencyResult,
    RetrievalResult,
)
from rag_benchmark.writers.csv_writer import write_latency_csv, write_retrieval_csv
from rag_benchmark.writers.json_writer import write_benchmark_json
from rag_benchmark.writers.markdown_writer import write_report_markdown


def _query(i: int) -> BenchmarkQuery:
    return BenchmarkQuery(
        id=i,
        query=f"query {i}",
        expected_document="doc.txt",
        expected_fields=["field_a"],
        document_type="Invoice",
        difficulty=Difficulty.EASY,
        tags=["retrieval"],
        template_id='Invoice'
    )


def test_write_benchmark_json_round_trips(tmp_path: Path) -> None:
    dataset = BenchmarkDataset(queries=[_query(1), _query(2)], template="generic")
    out = write_benchmark_json(dataset, tmp_path / "out" / "benchmark_queries.json")

    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert len(payload) == 2
    assert payload[0]["query"] == "query 1"
    assert payload[0]["difficulty"] == "easy"


def test_write_retrieval_csv_writes_headers_even_when_empty(tmp_path: Path) -> None:
    out = write_retrieval_csv([], tmp_path / "retrieval_metrics.csv")
    with out.open(encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
    assert header == ["query", "expected_document", "returned_document", "top_score", "success", "rank"]


def test_write_retrieval_csv_writes_rows(tmp_path: Path) -> None:
    results = [
        RetrievalResult(
            query="q1", expected_document="doc.txt", returned_document="doc.txt",
            top_score=0.95, success=True, rank=1,
        )
    ]
    out = write_retrieval_csv(results, tmp_path / "retrieval_metrics.csv")
    with out.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["query"] == "q1"
    assert rows[0]["success"] == "True"


def test_write_latency_csv_writes_headers(tmp_path: Path) -> None:
    out = write_latency_csv([], tmp_path / "latency_metrics.csv")
    with out.open(encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    assert header == [
        "query", "retriever_ms", "research_ms", "summarizer_ms", "citation_ms", "total_ms", "tokens",
    ]


def test_write_latency_csv_writes_rows(tmp_path: Path) -> None:
    results = [LatencyResult(query="q1", retriever_ms=10.0, total_ms=42.0, tokens=100)]
    out = write_latency_csv(results, tmp_path / "latency_metrics.csv")
    with out.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["tokens"] == "100"


def test_write_report_markdown_includes_key_sections(tmp_path: Path) -> None:
    stats = DatasetStatistics(
        total_documents=3,
        document_type_counts={"Invoice": 2, "Unknown": 1},
        total_questions=5,
        avg_questions_per_document=1.67,
        unknown_document_types=1,
        metadata_field_counts={"invoice_number": 2},
        warnings=["1 document(s) could not be classified."],
    )
    out = write_report_markdown(stats, tmp_path / "report.md", template_name="generic")
    content = out.read_text(encoding="utf-8")

    assert "# Benchmark Results" in content
    assert "generic" in content
    assert "Invoice" in content
    assert "invoice_number" in content
    assert "could not be classified" in content
