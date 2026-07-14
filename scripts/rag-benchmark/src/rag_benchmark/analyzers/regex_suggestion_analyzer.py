from rag_benchmark.diagnostics.models import RegexSuggestion
from rag_benchmark.suggestions.regex_suggestions import suggest_regex

class RegexSuggestionAnalyzer:

    @staticmethod
    def analyze(candidates):

        suggestions = []

        for candidate in candidates:

            suggestions.append(
                RegexSuggestion(
                    label=candidate.label,
                    occurrences=candidate.count,
                    regex=suggest_regex(candidate.label),
                )
            )

        return suggestions