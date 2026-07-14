from __future__ import annotations
import typer
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.logging import configure_logging, get_logger
from rag_benchmark.config import build_config
from rag_benchmark.io import ensure_writable
from rich.console import Console
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.metrics import compute_statistics
console = Console()

logger = get_logger("cli.report")

def run_report(
    cfg: BenchmarkConfig,
    *,
    verbose: bool = False,
    save_report: bool = False,
    file: str | None = None,
    dry_run: bool = False,
) -> None:
    """Run the pipeline and write a Markdown benchmark report."""
    configure_logging(verbose=verbose)

    pipeline = BenchmarkPipeline()
    classified_documents, dataset_result, template_def = pipeline.run(cfg)
    stats = compute_statistics(classified_documents, dataset_result)

    report_path = cfg.output / "benchmark_results_latest.md"
    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] would write report to {report_path}")
        console.print(stats.model_dump())
        raise typer.Exit(code=0)

    ensure_writable(report_path, force)
    from rag_benchmark.writers import write_report_markdown

    write_report_markdown(stats, report_path, template_name=dataset_result.template)
    console.print(f"[green]Report written[/green] -> {report_path}")
