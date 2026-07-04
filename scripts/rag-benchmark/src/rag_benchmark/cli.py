"""Typer-based command line interface for rag_benchmark.

Commands:
    init      Scaffold a benchmark.yaml config and dataset/output folders.
    scan      List documents discovered in the dataset directory.
    generate  Run the full pipeline and write benchmark_queries.json.
    report    Run the pipeline and write a Markdown summary report.
    validate  Validate an existing benchmark_queries.json for issues.
    export    Run the pipeline and write all output artifacts at once.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.metrics import compute_statistics, validate_dataset
from rag_benchmark.models import BenchmarkDataset, BenchmarkQuery
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.templates import available_builtin_templates
from rag_benchmark.utils import configure_logging, get_logger

app = typer.Typer(
    name="rag-benchmark",
    help="Generate benchmark datasets and evaluation assets from a document collection.",
    no_args_is_help=True,
)
console = Console()
logger = get_logger("cli")

DatasetOpt = Annotated[Path | None, typer.Option("--dataset", help="Dataset directory to scan.")]
OutputOpt = Annotated[Path | None, typer.Option("--output", help="Output directory for artifacts.")]
TemplateOpt = Annotated[
    str | None,
    typer.Option("--template", help="Template name, file path, or module path."),
]
ConfigOpt = Annotated[
    Path | None, typer.Option("--config", help="Path to benchmark.yaml.")
]
ForceOpt = Annotated[bool, typer.Option("--force", help="Overwrite existing output files.")]
VerboseOpt = Annotated[bool, typer.Option("--verbose", help="Enable INFO-level logging.")]
DryRunOpt = Annotated[
    bool, typer.Option("--dry-run", help="Show what would happen without writing files.")
]


def _build_config(
    dataset: Path | None,
    output: Path | None,
    template: str | None,
    config: Path | None,
) -> BenchmarkConfig:
    base = BenchmarkConfig.load(config)
    return base.with_overrides(dataset=dataset, output=output, template=template)


def _ensure_writable(path: Path, force: bool) -> None:
    if path.exists() and not force:
        console.print(
            f"[red]Refusing to overwrite existing file:[/red] {path} "
            "(use --force to overwrite)"
        )
        raise typer.Exit(code=1)


@app.command()
def init(
    output: Annotated[Path, typer.Option("--output", help="Directory to scaffold.")] = Path("."),
    template: TemplateOpt = "generic",
    force: ForceOpt = False,
) -> None:
    """Scaffold a benchmark.yaml config file and dataset/output directories."""
    configure_logging(verbose=True)
    config_path = output / "benchmark.yaml"
    _ensure_writable(config_path, force)

    cfg = BenchmarkConfig(
        dataset=output / "datasets",
        output=output / "benchmarks",
        template=template or "generic",
    )
    cfg.save(config_path)
    cfg.dataset.mkdir(parents=True, exist_ok=True)
    cfg.output.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]Initialized[/green] config at {config_path}")
    console.print(f"  dataset directory: {cfg.dataset}")
    console.print(f"  output directory:  {cfg.output}")
    console.print(f"  template:          {cfg.template}")
    console.print(f"\nAvailable built-in templates: {', '.join(available_builtin_templates())}")


@app.command()
def scan(
    dataset: DatasetOpt = None,
    config: ConfigOpt = None,
    verbose: VerboseOpt = False,
) -> None:
    """Scan the dataset directory and list discovered documents."""
    configure_logging(verbose=verbose)
    cfg = _build_config(dataset, None, None, config)

    pipeline = BenchmarkPipeline()
    try:
        files = pipeline.load_documents(cfg.dataset)
    except (FileNotFoundError, NotADirectoryError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    table = Table(title=f"Documents in {cfg.dataset}")
    table.add_column("File")
    table.add_column("Format")
    table.add_column("Size (bytes)", justify="right")

    for scanned in files:
        table.add_row(str(scanned.path.relative_to(cfg.dataset)), scanned.format.value, str(scanned.size_bytes))

    console.print(table)
    console.print(f"[green]{len(files)}[/green] supported document(s) found.")


@app.command()
def generate(
    dataset: DatasetOpt = None,
    output: OutputOpt = None,
    template: TemplateOpt = None,
    config: ConfigOpt = None,
    force: ForceOpt = False,
    verbose: VerboseOpt = False,
    dry_run: DryRunOpt = False,
) -> None:
    """Run the full pipeline and write benchmark_queries.json."""
    configure_logging(verbose=verbose)
    cfg = _build_config(dataset, output, template, config)

    pipeline = BenchmarkPipeline()
    classified_documents, dataset_result = pipeline.run(cfg)

    output_path = cfg.output / "benchmark_queries.json"
    if dry_run:
        console.print(
            f"[yellow]Dry run:[/yellow] would write {len(dataset_result.queries)} "
            f"question(s) from {len(classified_documents)} document(s) to {output_path}"
        )
        raise typer.Exit(code=0)

    _ensure_writable(output_path, force)
    from rag_benchmark.writers import write_benchmark_json

    write_benchmark_json(dataset_result, output_path)
    console.print(
        f"[green]Generated[/green] {len(dataset_result.queries)} question(s) "
        f"from {len(classified_documents)} document(s) -> {output_path}"
    )


@app.command()
def report(
    dataset: DatasetOpt = None,
    output: OutputOpt = None,
    template: TemplateOpt = None,
    config: ConfigOpt = None,
    force: ForceOpt = False,
    verbose: VerboseOpt = False,
    dry_run: DryRunOpt = False,
) -> None:
    """Run the pipeline and write a Markdown benchmark report."""
    configure_logging(verbose=verbose)
    cfg = _build_config(dataset, output, template, config)

    pipeline = BenchmarkPipeline()
    classified_documents, dataset_result = pipeline.run(cfg)
    stats = compute_statistics(classified_documents, dataset_result)

    report_path = cfg.output / "benchmark_results_latest.md"
    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] would write report to {report_path}")
        console.print(stats.model_dump())
        raise typer.Exit(code=0)

    _ensure_writable(report_path, force)
    from rag_benchmark.writers import write_report_markdown

    write_report_markdown(stats, report_path, template_name=dataset_result.template)
    console.print(f"[green]Report written[/green] -> {report_path}")


@app.command()
def validate(
    output: OutputOpt = None,
    config: ConfigOpt = None,
    verbose: VerboseOpt = False,
) -> None:
    """Validate an existing benchmark_queries.json for structural issues."""
    configure_logging(verbose=verbose)
    cfg = _build_config(None, output, None, config)
    queries_path = cfg.output / "benchmark_queries.json"

    if not queries_path.exists():
        console.print(f"[red]No benchmark_queries.json found at {queries_path}[/red]")
        raise typer.Exit(code=1)

    with queries_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    dataset_result = BenchmarkDataset(queries=[BenchmarkQuery(**item) for item in raw])
    report_result = validate_dataset(dataset_result)

    table = Table(title="Validation Issues")
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Query ID")
    table.add_column("Message")

    for issue in report_result.issues:
        style = "red" if issue.severity == "error" else "yellow"
        table.add_row(
            f"[{style}]{issue.severity}[/{style}]",
            issue.code,
            str(issue.query_id) if issue.query_id is not None else "-",
            issue.message,
        )

    if report_result.issues:
        console.print(table)
    else:
        console.print("[green]No issues found.[/green]")

    console.print(
        f"{report_result.error_count} error(s), {report_result.warning_count} warning(s)"
    )
    if report_result.has_errors:
        raise typer.Exit(code=1)


@app.command()
def export(
    dataset: DatasetOpt = None,
    output: OutputOpt = None,
    template: TemplateOpt = None,
    config: ConfigOpt = None,
    force: ForceOpt = False,
    verbose: VerboseOpt = False,
    dry_run: DryRunOpt = False,
) -> None:
    """Run the full pipeline and export all artifacts: JSON, CSV, and Markdown."""
    configure_logging(verbose=verbose)
    cfg = _build_config(dataset, output, template, config)

    pipeline = BenchmarkPipeline()
    classified_documents, dataset_result = pipeline.run(cfg)
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
        _ensure_writable(path, force)

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


if __name__ == "__main__":
    app()
