from __future__ import annotations

from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.templates import TemplateDefinition
from collections import Counter
from rag_benchmark.analyzers.regex_analyzer import RegexAnalyzer, LABEL_REGEX
from rag_benchmark.analyzers.regex_candidate_analyzer import RegexCandidateAnalyzer
from rag_benchmark.analyzers.regex_suggestion_analyzer import RegexSuggestionAnalyzer
from rag_benchmark.analyzers.unused_regex_analyzer import UnusedRegexAnalyzer
from rag_benchmark.analyzers.metadata_coverage import MetadataCoverageAnalyzer
from rag_benchmark.analyzers.question_coverage import QuestionCoverageAnalyzer
from rag_benchmark.analyzers.readiness_analyzer import ReadinessAnalyzer
from rag_benchmark.diagnostics.models import RegexCandidate


class InspectAnalyzer:

    @staticmethod
    def analyze(
        result: InspectResult,

    ) -> None:
        """
        Populate InspectResult with extra diagnostics.
        """
        template = result.template
        regex_stats = RegexAnalyzer.analyze(
            result.classified,
            result.template,
        )

        result.regex_stats = regex_stats

        labels = RegexCandidateAnalyzer.extract_candidate_labels(
            result.classified.document.text
        )

        result.regex_candidates = RegexCandidateAnalyzer.collect_candidates(
            result.classified.document.text
        )

        print(result.regex_candidates)
        print(type(result.regex_candidates))
        result.regex_suggestions = RegexSuggestionAnalyzer.analyze(
            result.regex_candidates,
        )


        result.unused_regex = UnusedRegexAnalyzer.analyze(
            result.regex_stats,
        )

        result.metadata_coverage = MetadataCoverageAnalyzer.analyze(
            result,
        )

        result.question_coverage = QuestionCoverageAnalyzer.analyze(
            result,
        )

        result.readiness = (
            ReadinessAnalyzer.analyze(
                result,
                result.metadata_coverage,
                result.question_coverage,
            )
        )