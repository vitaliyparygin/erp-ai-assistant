import json
import typer
from rag_benchmark.logging import configure_logging, get_logger
from rag_benchmark.config import build_config
from rich.console import Console
from rich.table import Table
from rag_benchmark.models import BenchmarkDataset, BenchmarkQuery
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.metrics import validate_dataset
console = Console()


def run_validate(
    cfg: BenchmarkConfig,
    *,
    verbose: bool = False,
    save_report: bool = False,
    file: str | None = None,
) -> None:
    """Validate an existing benchmark_queries.json for structural issues."""
    configure_logging(verbose=verbose)
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
