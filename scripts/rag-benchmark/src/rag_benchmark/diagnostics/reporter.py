"""Rendering for the diagnostics subsystem: Rich console output plus the
`diagnose_latest.md` markdown export.

This module owns all presentation. It never computes anything — every
number and piece of text it displays was already computed by
`analyzer.py`, `statistics.py`, or `recommendations.py`.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

from rag_benchmark.diagnostics import DiagnosticsReport
from rag_benchmark.diagnostics.analyzer import DocumentDiagnostic
from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.diagnostics.recommendations import (
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from rag_benchmark.diagnostics.statistics import (
    STATUS_EXCELLENT,
    STATUS_FAIR,
    STATUS_GOOD,
)
from rag_benchmark.utils import get_logger
from rich.text import Text
from rag_benchmark.suggestions.regex_suggestions import suggest_field_synonyms
from rag_benchmark.diagnostics.models import Recommendation
from rich.console import Console
console = Console()
logger = get_logger("diagnostics.reporter")

_SEVERITY_COLORS = {
    SEVERITY_CRITICAL: "red",
    SEVERITY_WARNING: "yellow",
    SEVERITY_INFO: "cyan",
}

_STATUS_COLORS = {
    STATUS_EXCELLENT: "green",
    STATUS_GOOD: "green",
    STATUS_FAIR: "yellow",
}
_DEFAULT_STATUS_COLOR = "red"





class DiagnosticsReporter:
    """Renders a DiagnosticsReport to a Rich console and/or Markdown."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    # -- Section 1: Pipeline Overview ------------------------------------

    def _build_overview_panel(self, report: DiagnosticsReport) -> Panel:
        config = report.pipeline_diagnostics.config
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan", justify="right")
        table.add_column()
        table.add_row("Dataset path", str(config.dataset))
        table.add_row("Output path", str(config.output))
        table.add_row("Template", report.pipeline_diagnostics.template.name)
        table.add_row("Reader", config.reader)
        table.add_row("Language", config.language)
        table.add_row("Question generator", config.question_generator)
        table.add_row(
            "Number of documents", str(len(report.pipeline_diagnostics.classified_documents))
        )
        return Panel(table, title="Pipeline Overview", border_style="cyan")

    def render_overview(self, report: DiagnosticsReport) -> None:
        self._console.print(self._build_overview_panel(report))

    # -- Section 2: Summary -----------------------------------------------

    def _build_summary_panel(self, report: DiagnosticsReport) -> Panel:
        diag = report.pipeline_diagnostics
        classification = report.classification
        with_metadata = sum(1 for d in diag.document_diagnostics if d.available_fields)
        total_questions = len(diag.dataset.queries)
        avg_questions = (
            round(total_questions / classification.total_documents, 2)
            if classification.total_documents
            else 0.0
        )

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", justify="right")
        table.add_column()
        table.add_row("Total documents", str(classification.total_documents))
        table.add_row("Classified", str(classification.classified_count))
        table.add_row("Unknown", str(classification.unknown_count))
        table.add_row("Metadata extracted", f"{with_metadata} document(s)")
        table.add_row("Questions generated", str(total_questions))
        table.add_row("Average questions per document", str(avg_questions))
        return Panel(table, title="Summary", border_style="blue")

    def render_summary(self, report: DiagnosticsReport) -> None:
        self._console.print(self._build_summary_panel(report))

    def render_overview_and_summary(self, report: DiagnosticsReport) -> None:
        """Render the overview and summary panels side by side."""
        self._console.print(
            Columns(
                [self._build_overview_panel(report), self._build_summary_panel(report)],
                equal=True,
                expand=True,
            )
        )

    # -- Section 3: Classification statistics ------------------------------

    def render_classification_table(self, report: DiagnosticsReport) -> None:
        table = Table(title="Classification Statistics", box=None, show_edge=False)
        table.add_column("Document Type")
        table.add_column("Count", justify="right")

        for doc_type, count in sorted(
            report.classification.counts.items(), key=lambda kv: -kv[1]
        ):
            style = "dim" if doc_type == "Unknown" else None
            table.add_row(doc_type, str(count), style=style)

        self._console.print(table)



    # -- Section 5: Metadata extraction report -------------------------------

    def render_metadata_coverage(self, report: DiagnosticsReport) -> None:
        if not report.metadata_coverage:
            self._console.print("[dim]No document types with expected metadata fields.[/dim]")
            return

        for coverage in report.metadata_coverage:
            table = Table(title=coverage.document_type, box=None, show_edge=False)
            table.add_column("Field")
            table.add_column("Coverage", justify="right")
            for field_coverage in coverage.fields:
                color = _coverage_color(field_coverage.coverage_percent)
                table.add_row(
                    field_coverage.field_name,
                    f"[{color}]{field_coverage.coverage_percent:.0f}%[/{color}]",
                )
            table.caption = f"Overall: {coverage.overall_coverage_percent:.0f}%"
            self._console.print(table)

    # -- Section 6: Missing metadata report ----------------------------------

    # def render_missing_metadata(self, report: DiagnosticsReport) -> None:
    #     with_missing = [
    #         d
    #         for d in report.pipeline_diagnostics.document_diagnostics
    #         if d.missing_fields and not d.is_unknown
    #     ]
    #     if not with_missing:
    #         self._console.print("[green]No missing metadata — every expected field was found.[/green]")
    #         return
    #
    #     tree = Tree("[bold]Missing Metadata[/bold]")
    #     for diag in with_missing:
    #         file_branch = tree.add(f"[bold]{diag.classified.document.filename}[/bold]")
    #         file_branch.add(f"Missing: {', '.join(diag.missing_fields)}")
    #         file_branch.add(
    #             f"Available: {', '.join(diag.available_fields) or '(none)'}"
    #         )
    #         suggestions_branch = file_branch.add("Suggestions")
    #         for missing_field in diag.missing_fields:
    #             hints = suggest_field_synonyms(missing_field)
    #             suggestions_branch.add(f"{missing_field}: add regex for {', '.join(hints)}")
    #             field_branch = suggestions_branch.add(
    #                 f"{missing_field}: add regex for {', '.join(hints)}"
    #             )
    #
    #             for label, regex in RegexAnalyzer.field_suggestions(
    #                                                     missing_field
    #                                                 ):
    #                 field_branch.add(Text(f"{label} → {regex}"))
    #
    #     self._console.print(tree)

    # -- Section 7: Question generation report -------------------------------

    def render_question_report(self, report: DiagnosticsReport) -> None:
        if not report.question_stats:
            self._console.print("[dim]No document types in scope for question generation.[/dim]")
            return

        table = Table(title="Question Generation Report")
        table.add_column("Document Type")
        table.add_column("Possible", justify="right")
        table.add_column("Generated", justify="right")
        table.add_column("Skipped", justify="right")
        table.add_column("Coverage", justify="right")

        for stats in report.question_stats:
            color = _coverage_color(stats.coverage_percent)
            table.add_row(
                stats.document_type,
                str(stats.possible),
                str(stats.generated),
                str(stats.skipped),
                f"[{color}]{stats.coverage_percent:.0f}%[/{color}]",
            )

        self._console.print(table)

    # -- Section 8: Question preview ------------------------------------------

    # def render_question_preview(self, report: DiagnosticsReport) -> None:
    #     documents_with_questions = [
    #         d for d in report.pipeline_diagnostics.document_diagnostics if d.questions
    #     ]
    #     if not documents_with_questions:
    #         self._console.print("[dim]No questions were generated.[/dim]")
    #         return
    #
    #     tree = Tree("[bold]Generated Questions[/bold]")
    #     for diag in documents_with_questions:
    #         file_branch = tree.add(f"[bold]{diag.classified.document.filename}[/bold]")
    #         for query in diag.questions:
    #             file_branch.add(query.query)
    #
    #     self._console.print(tree)
    #
    # # -- Section 9: Recommendations --------------------------------------------



    def render_recommendations(
            self,
            recommendations: list[Recommendation],
    ) -> None:
        if not recommendations:
            return

        table = Table(title="Recommendations")

        table.add_column("#", style="cyan", width=3)
        table.add_column("Severity")
        table.add_column("Context")
        table.add_column("Issue")
        table.add_column("Suggestion")

        for i, rec in enumerate(recommendations, 1):
            table.add_row(
                str(i),
                rec.severity,
                rec.context,
                rec.issue,
                rec.suggestion,
            )

        console.print(table)


    # -- Section 10: Overall Benchmark Readiness --------------------------------

    def render_readiness(self, report: DiagnosticsReport) -> None:
        scores = report.readiness
        status_color = _STATUS_COLORS.get(scores.status, _DEFAULT_STATUS_COLOR)

        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold", justify="right")
        table.add_column()
        table.add_row("Classification", f"{scores.classification_score:.0f}%")
        table.add_row("Extraction", f"{scores.extraction_score:.0f}%")
        table.add_row("Questions", f"{scores.question_score:.0f}%")
        table.add_row("Overall", f"[bold]{scores.overall_score:.0f}%[/bold]")
        table.add_row("Status", f"[bold {status_color}]{scores.status}[/bold {status_color}]")

        self._console.print(
            Panel(table, title="Overall Benchmark Readiness", border_style=status_color)
        )

    # -- Verbose mode: full per-document detail ---------------------------------

    def render_verbose_documents(self, report: DiagnosticsReport) -> None:
        tree = Tree("[bold]All Documents (verbose)[/bold]")
        for diag in report.pipeline_diagnostics.document_diagnostics:
            tree.add(self._verbose_document_branch(diag))
        self._console.print(tree)

    @staticmethod
    def _verbose_document_branch(diag: DocumentDiagnostic) -> Tree:
        branch = Tree(f"[bold]{diag.classified.document.filename}[/bold]")
        branch.add(f"Classification: {diag.classified.classification.document_type} "
                    f"(confidence {diag.classified.classification.confidence:.2f})")
        branch.add(f"Metadata: {diag.classified.metadata.as_plain_dict() or '(none)'}")
        branch.add(f"Missing fields: {', '.join(diag.missing_fields) or '(none)'}")
        questions_branch = branch.add(f"Generated questions ({len(diag.questions)})")
        for query in diag.questions:
            questions_branch.add(query.query)
        return branch

    # -- Orchestration -----------------------------------------------------

    def render(self, report: DiagnosticsReport, verbose: bool = False) -> None:
        """Render the complete diagnostics report to the console.

        Args:
            report: The computed DiagnosticsReport.
            verbose: If True, also render the per-document verbose section.
        """
        self._console.print(Rule("[bold]rag-benchmark diagnose[/bold]"))
        self.render_overview_and_summary(report)

        self._console.print(Rule("Classification"))
        self.render_classification_table(report)


        self._console.print(Rule("Metadata Extraction"))
        self.render_metadata_coverage(report)

        # self._console.print(Rule("Missing Metadata"))
        # self.render_missing_metadata(report)

        self._console.print(Rule("Question Generation"))
        self.render_question_report(report)
        # self.render_question_preview(report)

        self._console.print(Rule("Recommendations"))
        self.render_recommendations(report.recommendations)

        self._console.print(Rule("Readiness"))
        self.render_readiness(report)

        if verbose:
            self._console.print(Rule("Verbose: All Documents"))
            self.render_verbose_documents(report)


    # -- inspect: single-document deep dive -------------------------------

    def render_inspect(self, result: InspectResult) -> None:
        """Render a full single-document inspection.

        Args:
            result: The InspectResult produced by `diagnostics.inspect.inspect_document`.
        """
        file_table = Table.grid(padding=(0, 2))
        file_table.add_column(style="bold cyan", justify="right")
        file_table.add_column()
        file_table.add_row("Filename", result.scanned_file.path.name)
        file_table.add_row("Format", result.scanned_file.format.value)
        file_table.add_row("Size", f"{result.scanned_file.size_bytes} bytes")
        file_table.add_row("Modified", result.scanned_file.modified_at.isoformat())
        file_table.add_row(
            "Detected type",
            f"[bold]{result.classified.classification.document_type}[/bold] "
            f"(confidence {result.classified.classification.confidence:.2f})",
        )
        self._console.print(Panel(file_table, title="File Information", border_style="cyan"))

        metadata = result.classified.metadata.as_plain_dict()
        if metadata:
            metadata_table = Table(title="Extracted Metadata")
            metadata_table.add_column("Field")
            metadata_table.add_column("Value")
            for name, value in metadata.items():
                metadata_table.add_row(name, value)
            self._console.print(metadata_table)
        else:
            self._console.print("[yellow]No metadata extracted.[/yellow]")

        if result.missing_fields:
            self._console.print(
                Panel(
                    ", ".join(result.missing_fields),
                    title="Missing Fields",
                    border_style="yellow",
                )
            )

        if result.questions:
            questions_table = Table(title="Generated Questions")
            questions_table.add_column("#", justify="right")
            questions_table.add_column("Query")
            for i, query in enumerate(result.questions, start=1):
                questions_table.add_row(str(i), query.query)
            self._console.print(questions_table)
        else:
            self._console.print("[dim]No questions were generated for this document.[/dim]")

        self._console.print(
            Panel(
                Syntax(result.text_preview or "(empty document)", "text", word_wrap=True),
                title="Raw Text Preview",
                border_style="magenta",
            )
        )

        if result.is_unknown and result.suggested_rule:
            rule = result.suggested_rule
            suggestion_tree = Tree("[bold]Suggestions[/bold]")
            suggestion_tree.add(f"Create document type: [bold]{rule.document_type}[/bold]")
            suggestion_tree.add(f"Filename pattern: {rule.filename_pattern!r}")
            content_branch = suggestion_tree.add("Content pattern(s)")
            for pattern in rule.content_patterns or ["(none detected)"]:
                content_branch.add(pattern)
            if result.keywords:
                keywords_branch = suggestion_tree.add("Detected keywords")
                for keyword in result.keywords:
                    keywords_branch.add(keyword)
            self._console.print(suggestion_tree)
        elif result.missing_fields:
            suggestion_tree = Tree("[bold]Suggestions[/bold]")
            for missing_field in result.missing_fields:
                hints = suggest_field_synonyms(missing_field)
                suggestion_tree.add(f"{missing_field}: add regex for {', '.join(hints)}")
            self._console.print(suggestion_tree)


def _coverage_color(percent: float) -> str:
    if percent >= 90.0:
        return "green"
    if percent >= 50.0:
        return "yellow"
    return "red"


def generate_markdown_report(report: DiagnosticsReport, generated_at: datetime | None = None) -> str:
    """Render a DiagnosticsReport as a standalone Markdown document.

    Args:
        report: The computed DiagnosticsReport.
        generated_at: Timestamp to display; defaults to now (UTC).

    Returns:
        Markdown text ready to write to `diagnose_latest.md`.
    """
    generated_at = generated_at or datetime.utcnow()
    diag = report.pipeline_diagnostics
    config = diag.config

    lines: list[str] = [
        "# Diagnose Report",
        "",
        f"- **Generated at:** {generated_at.isoformat()} UTC",
        f"- **Dataset:** {config.dataset}",
        f"- **Template:** {diag.template.name}",
        "",
        "## Summary",
        "",
        f"- Total documents: {report.classification.total_documents}",
        f"- Classified: {report.classification.classified_count}",
        f"- Unknown: {report.classification.unknown_count}",
        f"- Questions generated: {len(diag.dataset.queries)}",
        "",
        "## Classification Statistics",
        "",
        "| Document Type | Count |",
        "|---|---|",
    ]
    for doc_type, count in sorted(report.classification.counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {doc_type} | {count} |")

    lines += ["", "## Metadata Extraction Coverage", ""]
    for coverage in report.metadata_coverage:
        lines.append(f"### {coverage.document_type}")
        lines.append("")
        lines.append("| Field | Coverage |")
        lines.append("|---|---|")
        for field_coverage in coverage.fields:
            lines.append(f"| {field_coverage.field_name} | {field_coverage.coverage_percent:.0f}% |")
        lines.append(f"\nOverall: {coverage.overall_coverage_percent:.0f}%\n")

    lines += ["## Question Generation", "", "| Document Type | Possible | Generated | Skipped | Coverage |", "|---|---|---|---|---|"]
    for stats in report.question_stats:
        lines.append(
            f"| {stats.document_type} | {stats.possible} | {stats.generated} | "
            f"{stats.skipped} | {stats.coverage_percent:.0f}% |"
        )

    lines += ["", "## Recommendations", ""]
    if report.recommendations:
        for rec in report.recommendations:
            lines.append(f"- **[{rec.severity.upper()}] {rec.context}**: {rec.issue} → {rec.suggestion}")
    else:
        lines.append("- None — the dataset looks benchmark-ready.")

    lines += [
        "",
        "## Overall Benchmark Readiness",
        "",
        f"- Classification: {report.readiness.classification_score:.0f}%",
        f"- Extraction: {report.readiness.extraction_score:.0f}%",
        f"- Questions: {report.readiness.question_score:.0f}%",
        f"- **Overall: {report.readiness.overall_score:.0f}%**",
        f"- **Status: {report.readiness.status}**",
        "",
    ]

    return "\n".join(lines)


def write_markdown_report(
    report: DiagnosticsReport, output_path: Path, generated_at: datetime | None = None
) -> Path:
    """Render and write the diagnostics Markdown report to disk.

    Args:
        report: The computed DiagnosticsReport.
        output_path: Destination file path (parent dirs are created).
        generated_at: Timestamp to display; defaults to now (UTC).

    Returns:
        The path written to.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_markdown_report(report, generated_at=generated_at)
    output_path.write_text(content, encoding="utf-8")
    logger.info("Wrote diagnostics report to %s", output_path)
    return output_path