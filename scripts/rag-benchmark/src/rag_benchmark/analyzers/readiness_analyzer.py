
from rag_benchmark.diagnostics.models import (ReadinessResult)
from rag_benchmark.diagnostics.inspect import InspectResult


class ReadinessAnalyzer:

    @staticmethod
    def analyze(
        result: InspectResult,
        metadata,
        questions,
    ):

        classification = (
            result.classified.classification.confidence * 100
        )

        overall = (
            classification
            + metadata.coverage
            + questions.coverage
        ) / 3

        return ReadinessResult(
            classification=classification,
            metadata=metadata.coverage,
            questions=questions.coverage,
            overall=overall,
        )