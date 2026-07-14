"""Writer for benchmark_results_latest.md."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rag_benchmark.models import DatasetStatistics
from rag_benchmark.logging import get_logger

logger = get_logger("writers.markdown")


def write_report_markdown(
    stats: DatasetStatistics,
    output_path: Path,
    template_name: str,
    generated_at: datetime | None = None,
) -> Path:
    """Render a DatasetStatistics summary as a Markdown report.

    Args:
        stats: Aggregate statistics to render.
        output_path: Destination file path (parent dirs are created).
        template_name: Name of the template used for this run.
        generated_at: Timestamp to display; defaults to now (UTC).

    Returns:
        The path written to.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = generated_at or datetime.utcnow()

    lines: list[str] = [
        "# Benchmark Results",
        "",
        f"- **Generated at:** {generated_at.isoformat()} UTC",
        f"- **Template:** {template_name}",
        "",
        "## Dataset Statistics",
        "",
        f"- Total documents scanned: {stats.total_documents}",
        f"- Total questions generated: {stats.total_questions}",
        f"- Average questions per document: {stats.avg_questions_per_document:.2f}",
        f"- Unknown document types: {stats.unknown_document_types}",
        "",
        "## Detected Document Types",
        "",
        "| Document Type | Count |",
        "|---|---|",
    ]

    for doc_type, count in sorted(stats.document_type_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {doc_type} | {count} |")

    lines += [
        "",
        "## Metadata Field Coverage",
        "",
        "| Field | Documents With Field |",
        "|---|---|",
    ]
    for field_name, count in sorted(stats.metadata_field_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {field_name} | {count} |")

    lines += ["", "## Warnings", ""]
    if stats.warnings:
        lines.extend(f"- {warning}" for warning in stats.warnings)
    else:
        lines.append("- None")

    content = "\n".join(lines) + "\n"
    output_path.write_text(content, encoding="utf-8")

    logger.info("Wrote markdown report to %s", output_path)
    return output_path
