from __future__ import annotations
from pathlib import Path
from typing import Annotated
import typer

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
SaveReportOpt = Annotated[
    bool, typer.Option("--save-report", help="Write diagnose_latest.md to the output directory.")
]
FileOpt = Annotated[
    str | None,
    typer.Option(
        "--file",
        help="Run diagnostics only for files matching this name.",
    ),
]