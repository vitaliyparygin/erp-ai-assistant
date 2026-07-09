from __future__ import annotations
from rich.tree import Tree
from rag_benchmark.models import BenchmarkQuery, ClassifiedDocument
from rag_benchmark.templates import TemplateDefinition
from rag_benchmark.diagnostics.models import DocumentDiagnostic, QuestionGeneration
from rich.console import Console
console = Console()

class QuestionGenerationAnalyzer:

    @staticmethod
    def analyze(
        classified: ClassifiedDocument,
        template: TemplateDefinition,
        questions: list[BenchmarkQuery],
    ) -> QuestionGeneration:

        specs = template.question_templates.get(
            classified.classification.document_type,
            (),
        )
        available = classified.metadata.as_plain_dict()
        generated_fields = {
            field
            for q in questions
            for field in q.expected_fields
        }

        possible = 0
        missing_fields: list[str] = []
        unused_templates: list[str] = []

        for spec in specs:
            template_used = False
            for field in spec.fields:
                possible += 1
                name = field.name
                if name in available:
                    template_used = True
                else:
                    missing_fields.append(name)

            if not template_used:
                unused_templates.append(spec.query_template)

        generated = len(questions)
        skipped = max(
            possible - generated,
            0,
        )
        coverage = (
            generated / possible
            if possible
            else 1.0
        )

        return QuestionGeneration(
            possible=possible,
            generated=generated,
            skipped=skipped,
            generated_fields=sorted(generated_fields),
            missing_fields=sorted(set(missing_fields)),
            unused_templates=unused_templates,
            coverage=coverage,
        )

    @staticmethod
    def report(
        diagnostics: list[DocumentDiagnostic],
    ):
        console.print()
        tree = Tree("[bold]Generated Questions[/bold]")
        for diag in diagnostics:
            if not diag.questions:
                continue
            doc = tree.add(diag.filename)
            for q in diag.questions:
                doc.add(q.query)

        console.print(tree)
