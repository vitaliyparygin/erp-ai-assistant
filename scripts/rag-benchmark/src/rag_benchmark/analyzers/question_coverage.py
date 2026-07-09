from __future__ import annotations
from rag_benchmark.diagnostics.models import (DocumentDiagnostic,
                                              QuestionCoverage)
from rich.tree import Tree
from rich.console import Console
console = Console()

class QuestionCoverageAnalyzer:
    """Analyze question generation coverage."""

    @staticmethod
    def analyze(
            diagnostic: DocumentDiagnostic,
    ) -> QuestionCoverage:
        generated = sorted(
            {
                field
                for q in diagnostic.questions
                for field in q.expected_fields
            }
        )

        missing = [
            f
            for f in diagnostic.expected_fields
            if f not in generated
        ]
        total = len(diagnostic.expected_fields)
        coverage = (
            len(generated) / total
            if total
            else 1.0
        )

        return QuestionCoverage(
            filename=diagnostic.filename,
            generated=generated,
            missing=missing,
            coverage=coverage,
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
                f"({result.coverage:.0%})"
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