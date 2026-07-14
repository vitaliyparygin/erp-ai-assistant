"""Typer-based command line interface for rag_benchmark.

Commands:
    init      Scaffold a benchmark.yaml config and dataset/output folders.
    scan      List documents discovered in the dataset directory.
    generate  Run the full pipeline and write benchmark_queries.json.
    report    Run the pipeline and write a Markdown summary report.
    validate  Validate an existing benchmark_queries.json for issues.
    export    Run the pipeline and write all output artifacts at once.
    diagnose  Run the full pipeline read-only and explain pipeline health.
    inspect   Deep-dive into a single document's pipeline journey.
"""
from __future__ import annotations
from pathlib import Path
from typing import Annotated
import typer
from rag_benchmark.config import build_config
from rag_benchmark.commands.init import run_init
from rag_benchmark.commands.generate import run_generate
from rag_benchmark.commands.report import run_report
from rag_benchmark.commands.export import run_export
from rag_benchmark.commands.diagnose import run_diagnose
from rag_benchmark.commands.inspect import run_inspection
from rag_benchmark.commands.validate import run_validate
from rag_benchmark.commands.scan import run_scan
from rich.console import Console
from rag_benchmark.cli.options import TemplateOpt, ForceOpt, VerboseOpt, DryRunOpt, OutputOpt, ConfigOpt,DatasetOpt, FileOpt, SaveReportOpt
from rag_benchmark.cli.app import app
console = Console()



def run_with_config(
    runner,
    dataset,
    output,
    template,
    config,
    verbose,
):

    cfg = build_config(
        dataset,
        output,
        template,
        config,
    )

    runner(cfg,verbose)

@app.command()
def init(
    output: Path = Path("."),
    template: TemplateOpt = "generic",
    force: ForceOpt = False,
):
    run_init(output, template, force)

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
    cfg = build_config(dataset, output, template, config)
    run_generate(cfg,  verbose=verbose, force=force, dry_run=dry_run)

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
    cfg = build_config(dataset, output, template, config)
    run_report(cfg,  verbose=verbose, force=force, dry_run=dry_run)

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
    cfg = build_config(dataset, output, template, config)
    run_export(cfg,  verbose=verbose, force=force, dry_run=dry_run)


@app.command()
def diagnose(
    dataset: DatasetOpt = None,
    output: OutputOpt = None,
    template: TemplateOpt = None,
    config: ConfigOpt = None,
    file: FileOpt = None,
    verbose: VerboseOpt = False,
    save_report: SaveReportOpt = False,
) -> None:
    cfg = build_config(dataset, output, template, config)
    run_diagnose(
        cfg,
        verbose=verbose,
        save_report=save_report,
        file=file,
    )

@app.command()
def inspect(
    dataset: DatasetOpt = None,
    output: OutputOpt = None,
    template: TemplateOpt = None,
    config: ConfigOpt = None,
    file: FileOpt = False,
    verbose: VerboseOpt = False,
    save_report: SaveReportOpt = False,
) -> None:
    cfg = build_config(dataset, output, template, config)
    run_inspection(
        cfg,
        verbose=verbose,
        save_report=save_report,
        file=file,
    )

@app.command()
def validate(
    dataset: DatasetOpt = None,
    output: OutputOpt = None,
    template: TemplateOpt = None,
    config: ConfigOpt = None,
    file: FileOpt = False,
    verbose: VerboseOpt = False,
    save_report: SaveReportOpt = False,
) -> None:
    cfg = build_config(dataset, output, template, config)
    run_validate(
        cfg,
        verbose=verbose,
        save_report=save_report,
        file=file,
    )

@app.command()
def scan(
    dataset: DatasetOpt = None,
    output: OutputOpt = None,
    template: TemplateOpt = None,
    config: ConfigOpt = None,
    file: FileOpt = False,
    verbose: VerboseOpt = False,
    save_report: SaveReportOpt = False,
) -> None:
    cfg = build_config(dataset, output, template, config)
    run_scan(
        cfg,
        verbose=verbose,
        save_report=save_report,
        file=file,
    )