from rag_benchmark.diagnostics.models import RegexStat
from rich.table import Table
from rich.markup import escape
from collections import defaultdict
from rag_benchmark.diagnostics.models import (DocumentDiagnostic, RegexCandidate, RegexSuggestion)
from rag_benchmark.suggestions.regex_suggestions import build_regex
from collections import Counter
from rich.console import Console
console = Console()

class RegexRenderer:

    @staticmethod
    def render_regex_stats(stats: list[RegexStat]) -> None:
        if not stats:
            return
        table = Table(title="Regex Analysis")
        table.add_column("Field")
        table.add_column("Matched")
        table.add_column("Pattern")
        for stat in stats:
            table.add_row(
                stat.field,
                "✓" if stat.matched else "✗",
                stat.pattern,
            )
        console.print(table)

    @staticmethod
    def render_regex_analysis(diagnostics: list[DocumentDiagnostic]):
        console.rule("Regex Analysis")
        for diag in diagnostics:
            if not diag.regex_stats:
                continue
            console.print(f"\n[bold]{diag.filename}[/bold]")
            grouped = defaultdict(list)
            for stat in diag.regex_stats:
                grouped[stat.field].append(stat)
            for field, stats in grouped.items():
                console.print(f"\n[cyan]{field}[/cyan]")
                for stat in stats:
                    if stat.matched:
                        console.print(
                            f"[green]✓[/green] {stat.pattern}"
                        )
                        if stat.matched_text:
                            console.print(
                                f"    matched : {stat.matched_text}"
                            )
                        if stat.value:
                            console.print(
                                f"    value   : {stat.value}"
                            )
                    else:
                        console.print(
                            f"[red]✗[/red] {stat.pattern}")

    @staticmethod
    def render_unused(stats: list[RegexStat]) -> None:
        """Print regexes that never matched and return their count."""
        unused = [s for s in stats if not s.matched]
        if not unused:
            return None
        table = Table(title="Regex Success Rate")
        table.add_column("Document")
        table.add_column("Field")
        table.add_column("Regex")

        for stat in unused:
            table.add_row(
                stat.document_type,
                stat.field,
                escape(stat.pattern),
            )
        console.print(table)
        console.print(f"\nUnused regexes: {len(unused)}")

    @staticmethod
    def render_candidate_regex(labels: Counter[str]) -> None:
        if not labels:
            return

        table = Table(title="Suggested Regex")

        table.add_column("Label")
        table.add_column("Occurrences")
        table.add_column("Regex")

        for label, count in labels.most_common():
            table.add_row(
                label,
                str(count),
                build_regex(label),
            )

        console.print(table)

    @staticmethod
    def render_regex_suggestions(
            suggestions: list[RegexSuggestion],
    ) -> None:
        table = Table(title="Suggested Regex")

        table.add_column("Label")
        table.add_column("Occurrences", justify="right")
        table.add_column("Suggested Regex")

        for suggestion in suggestions:

            table.add_row(
                suggestion.label,
                str(suggestion.count),
            )

        console.print(table)
