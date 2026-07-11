from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.renderers.regex_renderer import RegexRenderer
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from rag_benchmark.diagnostics.models import Recommendation
from rag_benchmark.diagnostics.reporter import InspectResult
from rag_benchmark.diagnostics.reporter import _STATUS_COLORS
console = Console()

class CommonRenderer:
    """Rich renderer for `rag-benchmark inspect`."""

    @staticmethod
    def render(
        report: InspectResult,
        recommendations: list[Recommendation],
    ) -> None:

        # CommonRenderer.render_classification(report)
        CommonRenderer.render_regex(report)
        CommonRenderer.render_question_coverage(report)
        # CommonRenderer.render_readiness(report)


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
    def render_question_coverage(report: InspectResult) -> None:
        if report.question_coverage is None:
            return

        qc = report.question_coverage

        table = Table(title="Question Coverage")

        table.add_column("Metric")
        table.add_column("Value")

        table.add_row(
            "Expected",
            str(qc.expected),
        )

        table.add_row(
            "Generated",
            str(qc.generated),
        )

        table.add_row(
            "Coverage",
            f"{qc.coverage:.1%}",
        )

        console.print(table)

    # @staticmethod
    # def render_question_coverage(report: DiagnosticsReporter) -> None:
    #     qc = getattr(report, "question_coverage", None)
    #
    #     if qc is None:
    #         return
    #
    #     table = Table(title="Question Coverage")
    #
    #     table.add_column("Metric")
    #     table.add_column("Value")
    #
    #     table.add_row("Expected", str(qc.expected_questions))
    #     table.add_row("Generated", str(qc.generated_questions))
    #     table.add_row("Missing", str(qc.missing_questions))
    #     table.add_row("Coverage", f"{qc.coverage:.1%}")
    #
    #     console.print(table)


    @staticmethod
    def render_classification(report: InspectResult) -> None:

        table = Table(title="Classification")

        table.add_column("Property")
        table.add_column("Value")

        table.add_row(
            "Detected",
            report.classified.classification.document_type,
        )

        table.add_row(
            "Confidence",
            f"{report.classified.classification.confidence:.2f}",
        )
        if getattr(report, "classification_scores", None):
            table.add_row(
                "Candidates",
                "",
            )

            for score in report.classification_scores:
                table.add_row(
                    f"  {score.document_type}",
                    f"{score.score:.2%}",
                )

        console.print(table)
