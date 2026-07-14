
from rag_benchmark.diagnostics.models import (ReadinessReport)
from rag_benchmark.diagnostics.inspect import InspectResult

class ReadinessAnalyzer:

    @staticmethod
    def analyze(
        result: InspectResult,
        metadata,
        questions,
        regex_score
    ):
        metadata_score = metadata.coverage
        question_score = questions.coverage
        regex_score = regex_score.coverage
        classification = result.classified.classification.confidence
        overall = (
                          classification
                          + metadata_score
                          + question_score
                          + regex_score
                  ) / 4

        return ReadinessReport(
            metadata_score=metadata.coverage,
            question_score=questions.coverage,
            overall_score = overall,
            regex_score = regex_score
        )