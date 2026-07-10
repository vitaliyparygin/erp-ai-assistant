from dataclasses import dataclass, field
from rag_benchmark.models import BenchmarkDataset, BenchmarkQuery, ClassifiedDocument
from rag_benchmark.classifier import UNKNOWN_TYPE
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.templates import TemplateDefinition
from datetime import datetime

#: Fields extracted in fewer than this percentage of documents are flagged
#: as "partially working" rather than "completely missing".
LOW_FIELD_COVERAGE_THRESHOLD = 50.0

#: Document types whose question-generation coverage falls below this are
#: flagged, since low coverage is almost always downstream of extraction gaps.
LOW_QUESTION_COVERAGE_THRESHOLD = 50.0

#: Cap on distinct "create a new template" recommendations, so a dataset
#: full of unrelated unknown documents doesn't flood the report.
MAX_TEMPLATE_RECOMMENDATIONS = 10

SEVERITY_CRITICAL = "critical"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


@dataclass(frozen=True)
class SuggestedClassificationRule:
    """A human-readable suggestion for classifying a currently-unknown document."""

    document_type: str
    filename_pattern: str
    content_patterns: list[str]

@dataclass(slots=True)
class QuestionCoverage:
    filename: str
    generated: list[str]
    missing: list[str]
    coverage: float

@dataclass
class DocumentDiagnostic:
    """Everything known about one document."""

    # original objects
    classified: ClassifiedDocument

    expected_fields: list[str]
    missing_fields: list[str]
    question_generation: QuestionGeneration | None
    questions: list[BenchmarkQuery] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    suggested_rule: SuggestedClassificationRule | None = None
    # analyzer results
    field_coverage: FieldCoverage | None = None
    regex_analysis: list[RegexStat] = field(default_factory=list)

    # presentation object
    summary: DocumentSummary | None = None



    @property
    def is_unknown(self) -> bool:
        return (
            self.classified.classification.document_type
            == UNKNOWN_TYPE
        )

    @property
    def available_fields(self) -> list[str]:
        return list(
            self.classified.metadata.fields.keys()
        )

    @property
    def filename(self) -> str:
        return self.classified.document.filename

    @property
    def document_type(self) -> str:
        return self.classified.classification.document_type

    @property
    def extracted_fields(self) -> list[str]:
        return list(self.classified.metadata.fields.keys())

    @property
    def metadata(self):
        return self.classified.metadata

    @property
    def classification(self):
        return self.classified.classification

    @property
    def document(self):
        return self.classified.document

    @property
    def field_coverage_ratio(self) -> float:
        if self.field_coverage is None:
            return 0.0
        return self.field_coverage.coverage


    @property
    def regex_stats(self) -> list[RegexStat]:
        return self.regex_analysis

    @property
    def generated_questions(self) -> int:
        if self.question_generation is None:
            return 0
        return self.question_generation.generated


    @property
    def skipped_questions(self) -> int:
        if self.question_generation is None:
            return 0
        return self.question_generation.skipped


    @property
    def question_coverage_ratio(self) -> float:
        if self.question_generation is None:
            return 0.0
        return self.question_generation.coverage

@dataclass
class PipelineDiagnostics:
    """Complete, descriptive snapshot of a single (dry) pipeline run."""

    config: BenchmarkConfig
    template: TemplateDefinition
    classified_documents: list[ClassifiedDocument]
    dataset: BenchmarkDataset
    document_diagnostics: list[DocumentDiagnostic]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def unknown_diagnostics(self) -> list[DocumentDiagnostic]:
        return [d for d in self.document_diagnostics if d.is_unknown]

@dataclass
class ClassificationStats:
    """Aggregate classification outcomes across the whole dataset."""

    counts: dict[str, int]
    total_documents: int
    classified_count: int
    unknown_count: int
    classification_rate: float





@dataclass
class DocumentTypeMetadataCoverage:
    """Metadata extraction coverage for one document type, field by field."""

    document_type: str
    fields: list[FieldCoverage]
    overall_coverage_percent: float

# @dataclass
# class DatasetCoverage:
#
# @dataclass
# class ExtractionCoverage:
#
# @dataclass
# class GenerationCoverage:
#
# @dataclass
# class TemplateCoverage:


@dataclass
class QuestionTypeStats:
    """Question-generation yield for one document type."""

    document_type: str
    possible: int
    generated: int
    skipped: int
    coverage_percent: float


@dataclass
class ReadinessScores:
    """Weighted readiness scores summarizing the whole diagnostic run."""

    classification_score: float
    extraction_score: float
    question_score: float
    overall_score: float
    status: str

@dataclass(frozen=True)
class Recommendation:
    """One actionable diagnostic finding."""

    context: str
    issue: str
    suggestion: str
    severity: str = SEVERITY_WARNING

@dataclass(slots=True)
class QuestionGeneration:
    """Question generation statistics for one document."""

    possible: int
    generated: int
    skipped: int
    generated_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    unused_templates: list[str] = field(default_factory=list)
    coverage: float = 0.0



@dataclass(slots=True)
class UnusedQuestionTemplate:
    document_type: str
    template: str

@dataclass
class FieldCoverage:
    """Coverage of a single expected metadata field across one document type."""

    field_name: str
    documents_with_field: int
    total_documents_of_type: int
    coverage_percent: float

@dataclass
class RegexStat:
    document_type: str
    field: str
    pattern: str
    matches: int
    matched: bool
    value: str | None
    matched_text: str | None = None


@dataclass(slots=True)
class FieldCoverageResult:
    """Field extraction statistics for a single document."""

    expected: list[str]
    extracted: list[str]
    missing: list[str]
    coverage: float

@dataclass
class DocumentSummary:
    filename: str
    document_type: str
    extracted_fields: list[str]
    missing_fields: list[str]
    regex_stats: list[RegexStat]
    field_coverage: float

@dataclass
class DiagnosticsReport:
    """Everything a diagnostics report needs to render, in one object."""

    pipeline_diagnostics: PipelineDiagnostics
    classification: ClassificationStats
    metadata_coverage: list[DocumentTypeMetadataCoverage]
    question_stats: list[QuestionTypeStats]
    readiness: ReadinessScores
    recommendations: list[Recommendation]

@dataclass
class RegexCandidate:
    label: str
    count: int
    regex: str
