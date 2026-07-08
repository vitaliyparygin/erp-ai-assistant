from __future__ import annotations

from dataclasses import dataclass

from rag_benchmark.models import BenchmarkQuery


@dataclass(slots=True)
class QuestionCoverage:
    """Question generation statistics for a single document."""

    generated: int
    skipped: int
    generated_fields: list[str]
    missing_fields: list[str]


class QuestionCoverageAnalyzer:
    """Analyze question generation coverage."""

    @staticmethod
    def analyze(
        expected_fields: list[str],
        questions: list[BenchmarkQuery],
    ) -> QuestionCoverage:
        generated_fields: list[str] = []

        for question in questions:
            generated_fields.extend(question.expected_fields)

        generated = len(generated_fields)
        skipped = max(0, len(expected_fields) - generated)
        missing_fields = list(set(expected_fields) - set(generated_fields))
        return QuestionCoverage(
            generated=generated,
            skipped=skipped,
            generated_fields=generated_fields,
            missing_fields=missing_fields,
        )