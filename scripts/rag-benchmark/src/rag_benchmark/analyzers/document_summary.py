from rag_benchmark.diagnostics.models import (
    QuestionCoverage,
    FieldCoverage,
    RegexStat,
    DocumentSummary,
    ClassifiedDocument
)
UNKNOWN_TYPE = "Unknown"

class DocumentSummaryAnalyzer:

    @staticmethod
    def analyze(
        classified: ClassifiedDocument,
        field_result: FieldCoverage,
        regex_result: list[RegexStat],
        question_generation: QuestionCoverage,
    ) -> DocumentSummary:

        return DocumentSummary(
            filename=classified.document.filename,
            document_type=classified.classification.document_type,
            extracted_fields=field_result.extracted,
            missing_fields=field_result.missing,
            regex_stats=regex_result,
            field_coverage=field_result.coverage,
        )