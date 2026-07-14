from __future__ import annotations
from pathlib import Path
from typing import Annotated
import typer
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.templates import available_builtin_templates
from rag_benchmark.logging import configure_logging, get_logger
from rag_benchmark.io import ensure_writable
from rag_benchmark.cli.options import  TemplateOpt, ForceOpt
from rich.console import Console
console = Console()

logger = get_logger("cli.init")


def run_init(
    output: Annotated[Path, typer.Option("--output", help="Directory to scaffold.")] = Path("."),
    template: TemplateOpt = "generic",
    force: ForceOpt = False,
) -> None:
    """Scaffold a benchmark.yaml config file and dataset/output directories."""
    configure_logging(verbose=True)
    config_path = output / "benchmark.yaml"
    ensure_writable(config_path, force)

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
