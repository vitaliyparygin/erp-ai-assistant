"""Writers for retrieval_metrics.csv and latency_metrics.csv.

These are placeholders for the future evaluation phase (running generated
queries against a live RAG API) but are fully functional writers today:
they accept whatever RetrievalResult / LatencyResult rows the caller has,
including an empty list, and always produce a correctly-headered CSV.
"""

from __future__ import annotations

import csv
from pathlib import Path

from rag_benchmark.models import LatencyResult, RetrievalResult
from rag_benchmark.logging import get_logger

logger = get_logger("writers.csv")

_RETRIEVAL_HEADERS = ["query", "expected_document", "returned_document", "top_score", "success", "rank"]
_LATENCY_HEADERS = [
    "query",
    "retriever_ms",
    "research_ms",
    "summarizer_ms",
    "citation_ms",
    "total_ms",
    "tokens",
]


def write_retrieval_csv(results: list[RetrievalResult], output_path: Path) -> Path:
    """Write retrieval evaluation results to retrieval_metrics.csv."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_RETRIEVAL_HEADERS)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "query": result.query,
                    "expected_document": result.expected_document,
                    "returned_document": result.returned_document or "",
                    "top_score": result.top_score if result.top_score is not None else "",
                    "success": result.success,
                    "rank": result.rank if result.rank is not None else "",
                }
            )

    logger.info("Wrote %d retrieval result row(s) to %s", len(results), output_path)
    return output_path


def write_latency_csv(results: list[LatencyResult], output_path: Path) -> Path:
    """Write latency evaluation results to latency_metrics.csv."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=_LATENCY_HEADERS)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "query": result.query,
                    "retriever_ms": result.retriever_ms,
                    "research_ms": result.research_ms,
                    "summarizer_ms": result.summarizer_ms,
                    "citation_ms": result.citation_ms,
                    "total_ms": result.total_ms,
                    "tokens": result.tokens,
                }
            )

    logger.info("Wrote %d latency result row(s) to %s", len(results), output_path)
    return output_path
