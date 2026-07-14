from __future__ import annotations
import typer
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.logging import configure_logging, get_logger
from rag_benchmark.analyzers.regex_analyzer import RegexAnalyzer
from rag_benchmark.config import build_config
from rag_benchmark.io import ensure_writable
from rich.console import Console
from rag_benchmark.config import BenchmarkConfig
console = Console()

logger = get_logger("cli.generate")

def run_generate(
    cfg: BenchmarkConfig,
    *,
    verbose: bool = False,
    save_report: bool = False,
    file: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Run the full pipeline and write benchmark_queries.json."""
    configure_logging(verbose=verbose)

    pipeline = BenchmarkPipeline()
    classified_documents, dataset_result, template_def = pipeline.run(cfg)

    console.rule("[bold blue]Regex diagnostics")
    print("======================")
    stats = []

    for document in classified_documents:
        stats.extend(
            RegexAnalyzer.analyze(
                document,
                template_def,
            )
        )

    output_path = cfg.output / "benchmark_queries.json"
    if dry_run:
        console.print(
            f"[yellow]Dry run:[/yellow] would write {len(dataset_result.queries)} "
            f"question(s) from {len(classified_documents)} document(s) to {output_path}"
        )
        raise typer.Exit(code=0)

    ensure_writable(output_path, force)
    from rag_benchmark.writers import write_benchmark_json

    write_benchmark_json(dataset_result, output_path)
    console.print(
        f"[green]Generated[/green] {len(dataset_result.queries)} question(s) "
        f"from {len(classified_documents)} document(s) -> {output_path}"
    )