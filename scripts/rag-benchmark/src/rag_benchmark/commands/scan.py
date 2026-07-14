from __future__ import annotations
import typer
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.logging import configure_logging, get_logger
from rag_benchmark.config import build_config
from rich.console import Console
from rich.table import Table
from rag_benchmark.config import BenchmarkConfig
console = Console()

logger = get_logger("cli.scan")

def run_scan(
    cfg: BenchmarkConfig,
    *,
    verbose: bool = False,
    save_report: bool = False,
    file: str | None = None,
) -> None:
    """Scan the dataset directory and list discovered documents."""
    configure_logging(verbose=verbose)

    pipeline = BenchmarkPipeline()
    try:
        files = pipeline.scan(cfg.dataset)
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