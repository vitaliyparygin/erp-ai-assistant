
from __future__ import annotations
import typer
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.logging import configure_logging, get_logger
from rag_benchmark.config import build_config
from rich.console import Console
from rag_benchmark.diagnostics.inspect import (
    DocumentNotFoundError,
    UnsupportedDocumentError,
    inspect_document,
)
from rag_benchmark.diagnostics.analyzers.inspect_analyzer import InspectAnalyzer
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.diagnostics.inspect_recommendations.document import generate_document_recommendations
from rag_benchmark.diagnostics.renderers.inspect_renderer import InspectRenderer

console = Console()
logger = get_logger("cli.inspect")

def run_inspection(
    cfg: BenchmarkConfig,
    *,
    verbose: bool = False,
    save_report: bool = False,
    file: str | None = None,
) -> None:
    """Deep-dive into a single document: classification, metadata, questions, raw text."""
    configure_logging(verbose=verbose)
    pipeline = BenchmarkPipeline()
    print(pipeline, cfg, file)
    try:
        result = inspect_document(pipeline, cfg, file)
    except (DocumentNotFoundError, UnsupportedDocumentError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc

    InspectAnalyzer.analyze(
        result,
    )

    recommendations = generate_document_recommendations(
        result,
    )

    InspectRenderer.render(
        result,
        recommendations,
    )