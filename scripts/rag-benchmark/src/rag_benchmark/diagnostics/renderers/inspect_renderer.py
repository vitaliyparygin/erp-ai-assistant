from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.diagnostics.renderers.common_renderer import CommonRenderer
from rich.table import Table
from rich.panel import Panel
from rich.console import Console
from collections import defaultdict
from rag_benchmark.diagnostics.models import Recommendation
console = Console()

class InspectRenderer:
    """Rich renderer for `rag-benchmark inspect`."""

    @staticmethod
    def render(
        report: InspectResult,
        recommendations: list[Recommendation],
    ) -> None:

        CommonRenderer.render_file_information(report)

        CommonRenderer.render_classification(report)
        CommonRenderer.render_keywords(report)

        InspectRenderer.render_metadata(report)
        CommonRenderer.render_metadata_details(report)

        InspectRenderer.render_questions(report)
        CommonRenderer.render_question_coverage(report)

        InspectRenderer.render_preview(report)

        CommonRenderer.render_regex(report)
        CommonRenderer.render_regex_coverage(report)

        InspectRenderer.render_template_suggestions(report)

        CommonRenderer.render_readiness(report)
        InspectRenderer.render_missing_improvements(report)
        CommonRenderer.render_recommendations(recommendations)



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




    # @staticmethod
    # def render_template_suggestions(report: InspectResult) -> None:
    #     suggestions = getattr(report, "template_suggestions", None)
    #
    #     if not suggestions:
    #         return
    #
    #     table = Table(title="Suggested Template Additions")
    #
    #     table.add_column("#", justify="right")
    #     table.add_column("Suggested Field")
    #
    #     for i, field in enumerate(suggestions, 1):
    #         table.add_row(str(i), field)
    #
    #     console.print(table)



    # @staticmethod
    # def render_keywords(report: InspectResult) -> None:
    #     if not getattr(report, "matched_keywords", None):
    #         return
    #
    #     table = Table(title="Matched Keywords")
    #     table.add_column("#", justify="right")
    #     table.add_column("Keyword")
    #
    #     for i, keyword in enumerate(report.matched_keywords, 1):
    #         table.add_row(str(i), keyword)
    #
    #     console.print(table)


    # @staticmethod
    # def render_metadata_details(report: InspectResult) -> None:
    #     if not getattr(report, "metadata_details", None):
    #         return
    #
    #     table = Table(title="Metadata Extraction Details")
    #
    #     table.add_column("Field")
    #     table.add_column("Matched")
    #     table.add_column("Regex")
    #     table.add_column("Value")
    #
    #     for item in report.metadata_details:
    #         table.add_row(
    #             item["field"],
    #             "✓" if item["status"] else "✗",
    #             item["pattern"],
    #             item.get("matched", ""),
    #         )
    #
    #     console.print(table)






    # @staticmethod
    # def render_regex_coverage(report: InspectResult) -> None:
    #     if report.regex_coverage is None:
    #         return
    #
    #     rc = report.regex_coverage
    #
    #     table = Table(title="Regex Coverage")
    #
    #     table.add_column("Metric")
    #     table.add_column("Value")
    #
    #     table.add_row("Matched", str(rc.matched))
    #     table.add_row("Missing", str(rc.missing))
    #     table.add_row("Coverage", f"{rc.coverage:.1%}")
    #
    #     console.print(table)



    @staticmethod
    def render_template_suggestions(report: InspectResult) -> None:
        if not report.template_suggestions:
            return

        table = Table(title="Suggested Template Additions")

        table.add_column("#")
        table.add_column("Field")
        table.add_column("Reason")

        for i, suggestion in enumerate(report.template_suggestions, 1):
            table.add_row(
                str(i),
                suggestion.field,
                suggestion.reason,
            )
        console.print(table)


    @staticmethod
    def render_missing_improvements(report: InspectResult) -> None:
        improvements = getattr(report, "missing_improvements", None)
        if not improvements:
            return

        grouped = defaultdict(list)

        for item in improvements:
            grouped[item.category].append(item)

        table = Table(title="Missing Improvements")

        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Item", style="yellow")
        table.add_column("Suggestion")

        first = True

        for category in sorted(grouped):
            for improvement in grouped[category]:
                table.add_row(
                    category if first else "",
                    improvement.item,
                    improvement.suggestion,
                )
                first = False

            first = True
            table.add_section()

        console.print(table)