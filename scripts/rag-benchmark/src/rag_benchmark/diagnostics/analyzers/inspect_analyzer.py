from __future__ import annotations

from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.analyzers.regex_analyzer import RegexAnalyzer
from rag_benchmark.analyzers.regex_candidate_analyzer import RegexCandidateAnalyzer
from rag_benchmark.analyzers.regex_suggestion_analyzer import RegexSuggestionAnalyzer
from rag_benchmark.analyzers.unused_regex_analyzer import UnusedRegexAnalyzer
from rag_benchmark.analyzers.metadata_coverage import MetadataCoverageAnalyzer
from rag_benchmark.analyzers.question_coverage import QuestionCoverageAnalyzer
from rag_benchmark.analyzers.readiness_analyzer import ReadinessAnalyzer
from rag_benchmark.diagnostics.analyzers.keyword_analyzer import KeywordAnalyzer
from rag_benchmark.diagnostics.analyzers.template_suggestion_analyzer import TemplateSuggestionAnalyzer
from rag_benchmark.diagnostics.analyzers.metadata_details_analyzer import MetadataDetailsAnalyzer
from rag_benchmark.diagnostics.analyzers.regex_analyzer import RegexCoverageAnalyzer
from rag_benchmark.diagnostics.analyzers.missing_improvements_analyzer import MissingImprovementsAnalyzer
from rag_benchmark.diagnostics.models import ClassificationScore
class InspectAnalyzer:

    @staticmethod
    def analyze(
        result: InspectResult,

    ) -> None:
        """
        Populate InspectResult with extra diagnostics.
        """
        template = result.question_templates
        regex_stats = RegexAnalyzer.analyze(
            result.classified,
            result.question_templates,
        )

        result.regex_stats = regex_stats

        labels = RegexCandidateAnalyzer.extract_candidate_labels(
            result.classified.document.text
        )
        result.regex_candidates = RegexCandidateAnalyzer.collect_candidates(
            result.classified.document.text
        )

        result.classification_scores = [
            ClassificationScore(
                document_type=c.document_type,
                score=c.confidence,
            )
            for c in result.classified.classification.candidates
        ]

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
        result.regex_coverage = RegexCoverageAnalyzer.analyze(
            result,
        )
        result.missing_improvements = MissingImprovementsAnalyzer.analyze(result)
        result.readiness = (
            ReadinessAnalyzer.analyze(
                result,
                result.metadata_coverage,
                result.question_coverage,
                result.regex_coverage,
            )
        )

        # result.matched_keywords = KeywordAnalyzer.analyze(
        #     result.classified,
        # )

        result.metadata_details = MetadataDetailsAnalyzer.analyze(
            result,
        )



        result.template_suggestions = TemplateSuggestionAnalyzer.analyze(
            result,
        )
