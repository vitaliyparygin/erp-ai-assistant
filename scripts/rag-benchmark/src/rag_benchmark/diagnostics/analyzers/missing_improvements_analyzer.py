
from __future__ import annotations
from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.diagnostics.models import MissingImprovement

class MissingImprovementsAnalyzer:

    @staticmethod
    def analyze(result: InspectResult) -> list[MissingImprovement]:
        improvements = []
        for field in result.missing_fields:
            improvements.append(
                MissingImprovement(
                    category="Metadata",
                    item=field,
                    suggestion=f"Add regex for '{field}'",
                )
            )

        for stat in result.regex_stats:
            if not stat.matched:
                improvements.append(
                    MissingImprovement(
                        category="Regex",
                        item=stat.field,
                        suggestion=f"Regex does not match '{stat.field}'",
                    )
                )
        template = result.question_templates

        question_specs = template.question_templates.get(
            result.classified.classification.document_type,
            [],
        )

        expected = {
            field.name
            for spec in question_specs
            for field in spec.fields
        }
        generated = {
            q.field
            for q in result.questions
            if hasattr(q, "field")
        }

        for field in sorted(expected - generated):
            improvements.append(
                MissingImprovement(
                    category="Questions",
                    item=field,
                    suggestion=f"Question was not generated",
                )
            )

        return improvements