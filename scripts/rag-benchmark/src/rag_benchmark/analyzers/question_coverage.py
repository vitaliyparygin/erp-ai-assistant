from __future__ import annotations
from rag_benchmark.diagnostics.models import (DocumentDiagnostic,
                                              QuestionCoverageResult)
from rag_benchmark.diagnostics.inspect import InspectResult
from rich.tree import Tree
from rich.console import Console
console = Console()

class QuestionCoverageAnalyzer:
    """Analyze question generation coverage."""


    @staticmethod
    def analyze(result: InspectResult):

        expected = len(result.expected_fields)
        generated = len(result.questions)

        return QuestionCoverageResult(
            expected=expected,
            generated=generated,
            coverage=(
                generated / expected
                if expected else 100
            ),
        )

    @staticmethod
    def report(
            diagnostics: list[DocumentDiagnostic],
    ):

        console.rule("[bold]Question Coverage[/bold]")
        for diag in diagnostics:
            result = QuestionCoverageAnalyzer.analyze(
                diag,
            )
            tree = Tree(
                f"[cyan]{result.filename}[/cyan] "
                f"({result.coverage:.%})"
            )
            generated = tree.add("[green]Generated[/green]")
            if result.generated:
                for field in result.generated:
                    generated.add(field)
            else:
                generated.add("(none)")
            missing = tree.add("[red]Missing[/red]")
            if result.missing:
                for field in result.missing:
                    missing.add(field)
            else:
                missing.add("(none)")

            console.print(tree)