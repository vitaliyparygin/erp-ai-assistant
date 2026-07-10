from __future__ import annotations

from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.templates import TemplateDefinition
from collections import Counter
from rag_benchmark.analyzers.regex_analyzer import RegexAnalyzer, LABEL_REGEX
from rag_benchmark.analyzers.regex_candidate_analyzer import RegexCandidateAnalyzer

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