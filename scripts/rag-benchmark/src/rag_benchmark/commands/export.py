from __future__ import annotations
import typer
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.logging import configure_logging, get_logger
from rag_benchmark.config import build_config
from rag_benchmark.io import ensure_writable
from rich.console import Console
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.metrics import compute_statistics, validate_dataset
console = Console()

logger = get_logger("cli.export")

def run_export(
    cfg: BenchmarkConfig,
    *,
    verbose: bool = False,
    save_report: bool = False,
    file: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Run the full pipeline and export all artifacts: JSON, CSV, and Markdown."""
    configure_logging(verbose=verbose)

    pipeline = BenchmarkPipeline()
    classified_documents, dataset_result, template_def = pipeline.run(cfg)
    stats = compute_statistics(classified_documents, dataset_result)

    json_path = cfg.output / "benchmark_queries.json"
    retrieval_csv_path = cfg.output / "retrieval_metrics.csv"
    latency_csv_path = cfg.output / "latency_metrics.csv"
    report_path = cfg.output / "benchmark_results_latest.md"

    if dry_run:
        console.print("[yellow]Dry run:[/yellow] would write the following artifacts:")
        for path in (json_path, retrieval_csv_path, latency_csv_path, report_path):
            console.print(f"  - {path}")
        raise typer.Exit(code=0)

    for path in (json_path, retrieval_csv_path, latency_csv_path, report_path):
        ensure_writable(path, force)

    from rag_benchmark.writers import (
        write_benchmark_json,
        write_latency_csv,
        write_report_markdown,
        write_retrieval_csv,
    )

    write_benchmark_json(dataset_result, json_path)
    write_retrieval_csv([], retrieval_csv_path)
    write_latency_csv([], latency_csv_path)
    write_report_markdown(stats, report_path, template_name=dataset_result.template)

    console.print(f"[green]Exported[/green] {len(dataset_result.queries)} question(s):")
    console.print(f"  - {json_path}")
    console.print(f"  - {retrieval_csv_path} (scaffold, ready for evaluation results)")
    console.print(f"  - {latency_csv_path} (scaffold, ready for evaluation results)")
    console.print(f"  - {report_path}")