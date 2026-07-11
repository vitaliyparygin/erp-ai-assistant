from __future__ import annotations
from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.diagnostics.models import TemplateSuggestion

class TemplateSuggestionAnalyzer:

    @staticmethod
    def analyze(
        result: InspectResult,
    ) -> list[TemplateSuggestion]:

        suggestions = []

        for field in result.missing_fields:

            suggestions.append(
                TemplateSuggestion(
                    field=field,
                    reason="Missing metadata field",
                )
            )

        return suggestions