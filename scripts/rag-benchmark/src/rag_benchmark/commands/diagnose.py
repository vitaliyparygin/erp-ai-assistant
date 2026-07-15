from __future__ import annotations
import typer
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.logging import configure_logging, get_logger
from rich.console import Console
from rag_benchmark.config import BenchmarkConfig
from rich.progress import Progress, SpinnerColumn, TextColumn
from rag_benchmark.diagnostics.runner import build_diagnostics_report
from rag_benchmark.diagnostics.reporter import DiagnosticsReporter, write_markdown_report
console = Console()

logger = get_logger("cli.diagnose")

def run_diagnose(
    cfg: BenchmarkConfig,
    *,
    verbose: bool = False,
    save_report: bool = False,
    file: str | None = None,
) -> None:
    """Run the full pipeline read-only and diagnose why generation succeeds or fails.

    Executes every stage (scan, classify, extract, generate) exactly as
    `generate` would, but never writes benchmark_queries.json. Use
    --save-report to additionally write diagnose_latest.md.
    """
    configure_logging(verbose=verbose)
    pipeline = BenchmarkPipeline()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Running diagnostics pipeline...", total=None)
        try:
            report_result = build_diagnostics_report(
                pipeline,
                cfg,
                file=file,
            )
        except (FileNotFoundError, NotADirectoryError) as exc:
            console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=1) from exc
        progress.update(task, completed=1)

    reporter = DiagnosticsReporter(console=console)
    reporter.render(report_result, verbose=verbose)

    if save_report:
        report_path = cfg.output / "diagnose_latest.md"
        write_markdown_report(report_result, report_path)
        console.print(f"\n[green]Diagnostics report saved[/green] -> {report_path}")