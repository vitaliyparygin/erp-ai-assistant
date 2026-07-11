
from __future__ import annotations
from rag_benchmark.diagnostics.inspect import InspectResult
from rag_benchmark.diagnostics.models import RegexCoverage


class RegexCoverageAnalyzer:

    @staticmethod
    def analyze(
        result: InspectResult,
    ) -> RegexCoverage:

        matched = sum(
            stat.matched
            for stat in result.regex_stats
        )

        total = len(result.regex_stats)

        return RegexCoverage(
            matched=matched,
            missing=total - matched,
            coverage=matched / total if total else 0.0,
            total=total
        )