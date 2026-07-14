from __future__ import annotations
from pathlib import Path
import typer
from rich.console import Console
console = Console()


def ensure_writable(path: Path, force: bool) -> None:
    if path.exists() and not force:
        console.print(
            f"[red]Refusing to overwrite existing file:[/red] {path} "
            "(use --force to overwrite)"
        )
        raise typer.Exit(code=1)