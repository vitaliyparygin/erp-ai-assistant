
from __future__ import annotations

from dataclasses import dataclass
from rag_benchmark.models import ClassifiedDocument

@dataclass
class FieldCoverage:
    """Coverage of a single expected metadata field across one document type."""

    field_name: str
    documents_with_field: int
    total_documents_of_type: int
    coverage_percent: float

@dataclass(slots=True)
class FieldCoverageResult:
    """Field extraction statistics for a single document."""

    expected: list[str]
    extracted: list[str]
    missing: list[str]
    coverage: float

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