from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.renderers.regex_renderer import RegexRenderer
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rag_benchmark.diagnostics.models import Recommendation
console = Console()

class InspectRenderer:
    """Rich renderer for `rag-benchmark inspect`."""

    @staticmethod
    def render(
        report: InspectResult,
        recommendations: list[str],
    ) -> None:
        InspectRenderer.render_file_information(report)
        InspectRenderer.render_metadata(report)
        InspectRenderer.render_questions(report)
        InspectRenderer.render_preview(report)
        InspectRenderer.render_regex(report)
        InspectRenderer.render_recommendations(recommendations)

    @staticmethod
    def render_file_information(report: InspectResult) -> None:
        scanned = report.scanned_file
        classification = report.classified.classification

        table = Table(title="File Information")
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        table.add_row("Filename", scanned.path.name)
        table.add_row("Format", scanned.format.value)
        table.add_row("Size", f"{scanned.size_bytes} bytes")
        table.add_row("Modified", scanned.modified_at.isoformat())
        table.add_row(
            "Detected type",
            f"{classification.document_type} "
            f"(confidence {classification.confidence:.2f})",
        )

        console.print(table)

    @staticmethod
    def render_metadata(report: InspectResult) -> None:
        table = Table(title="Extracted Metadata")
        table.add_column("Field")
        table.add_column("Value")

        for key, value in sorted(report.classified.metadata.fields.items()):
            table.add_row(key, str(value))

        console.print(table)

        if report.missing_fields:
            console.print(
                Panel(
                    ", ".join(report.missing_fields),
                    title="Missing Fields",
                )
            )

    @staticmethod
    def render_questions(report: InspectResult) -> None:
        table = Table(title="Generated Questions")
        table.add_column("#")
        table.add_column("Query")

        for i, q in enumerate(report.questions, 1):
            table.add_row(str(i), q.query)

        console.print(table)

    @staticmethod
    def render_preview(report: InspectResult) -> None:
        console.print(
            Panel(
                report.text_preview,
                title="Raw Text Preview",
            )
        )

    @staticmethod
    def render_regex(report: InspectResult) -> None:
        if getattr(report, "regex_stats", None):
            RegexRenderer.render_regex_stats(
                report.regex_stats
            )

        if report.regex_candidates:
            RegexRenderer.render_regex_suggestions(
                report.regex_candidates
            )

    @staticmethod
    def render_recommendations(
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