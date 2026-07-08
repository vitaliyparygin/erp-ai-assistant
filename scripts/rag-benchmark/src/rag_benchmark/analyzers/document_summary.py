from __future__ import annotations

from dataclasses import dataclass

from rag_benchmark.analyzers.field_coverage import FieldCoverage
from rag_benchmark.analyzers.question_coverage import QuestionCoverage
from rag_benchmark.analyzers.regex_analyzer import RegexStat
from rag_benchmark.models import ClassifiedDocument

UNKNOWN_TYPE = "Unknown"

@dataclass
class DocumentSummary:
    filename: str
    document_type: str

    extracted_fields: list[str]
    missing_fields: list[str]

    regex_stats: list[RegexStat]

    generated_questions: int
    skipped_questions: int

    field_coverage: float
    # @property
    # def generated_questions(self) -> int:
    #     return (
    #         self.question_coverage.generated
    #         if self.question_coverage
    #         else 0
    #     )
    #
    #
    # @property
    # def skipped_questions(self) -> int:
    #     return (
    #         self.question_coverage.skipped
    #         if self.question_coverage
    #         else 0
    #     )


class DocumentSummaryAnalyzer:

    @staticmethod
    def analyze(
        classified: ClassifiedDocument,
        field_result: FieldCoverage,
        regex_result: list[RegexStat],
        question_result: QuestionCoverage,
    ) -> DocumentSummary:

        return DocumentSummary(
            filename=classified.document.filename,
            document_type=classified.classification.document_type,

            extracted_fields=field_result.extracted,
            missing_fields=field_result.missing,

            regex_stats=regex_result,

            generated_questions=question_result.generated,
            skipped_questions=question_result.skipped,

            field_coverage=field_result.coverage,
        )