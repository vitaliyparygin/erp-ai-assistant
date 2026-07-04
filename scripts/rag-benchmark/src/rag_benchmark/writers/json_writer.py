"""Writer for benchmark_queries.json."""

from __future__ import annotations

import json
from pathlib import Path

from rag_benchmark.models import BenchmarkDataset
from rag_benchmark.utils import get_logger

logger = get_logger("writers.json")


def write_benchmark_json(dataset: BenchmarkDataset, output_path: Path) -> Path:
    """Write a BenchmarkDataset's queries to a JSON file.

    Args:
        dataset: The dataset to serialize.
        output_path: Destination file path (parent dirs are created).

    Returns:
        The path written to.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = [
        json.loads(query.model_dump_json()) for query in dataset.queries
    ]

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    logger.info("Wrote %d queries to %s", len(dataset.queries), output_path)
    return output_path
