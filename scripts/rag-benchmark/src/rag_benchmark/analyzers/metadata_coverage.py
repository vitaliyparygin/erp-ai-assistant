from rag_benchmark.diagnostics.models import MetadataCoverageResult
from rag_benchmark.diagnostics.inspect import InspectResult


class MetadataCoverageAnalyzer:

    @staticmethod
    def analyze(result: InspectResult):

        expected = len(result.expected_fields)
        extracted = len(result.classified.metadata.fields)

        return MetadataCoverageResult(
            expected=expected,
            extracted=extracted,
            missing=expected-extracted,
            coverage=(
                extracted / expected * 100
                if expected else 100
            ),
        )