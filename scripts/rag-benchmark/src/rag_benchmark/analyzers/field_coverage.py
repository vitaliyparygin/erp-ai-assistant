from __future__ import annotations
from rag_benchmark.models import ClassifiedDocument
from rag_benchmark.diagnostics.models import FieldCoverageResult

class FieldCoverageAnalyzer:
    """Analyze extracted metadata coverage for one document."""

    @staticmethod
    def analyze(
        classified: ClassifiedDocument,
        expected_fields: list[str],
    ) -> FieldCoverageResult:
        available = list(classified.metadata.fields.keys())

        missing = [
            field
            for field in expected_fields
            if field not in available
        ]

        coverage = (
            len(available) / len(expected_fields)
            if expected_fields
            else 1.0
        )

        return FieldCoverageResult(
            expected=expected_fields,
            extracted=available,
            missing=missing,
            coverage=coverage,
        )