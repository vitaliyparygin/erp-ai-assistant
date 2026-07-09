"""Core data models shared across the rag_benchmark package.

All cross-module data contracts live here so that scanner, reader,
classifier, extractor, generators and writers can depend on a single,
stable set of types instead of on each other.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from dataclasses import dataclass, field

class DocumentFormat(str, Enum):
    """Supported raw document formats."""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    UNKNOWN = "unknown"


class Difficulty(str, Enum):
    """Difficulty tiers for generated benchmark questions."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ScannedFile(BaseModel):
    """A single file discovered on disk by the scanner, prior to reading."""

    path: Path
    format: DocumentFormat
    size_bytes: int
    modified_at: datetime

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("path")
    @classmethod
    def _resolve_path(cls, value: Path) -> Path:
        return Path(value)


class Document(BaseModel):
    """A document that has been read into memory as normalized text."""

    id: str
    path: Path
    filename: str
    format: DocumentFormat
    text: str
    page_count: int | None = None
    char_count: int = 0

    model_config = {"arbitrary_types_allowed": True}


class ClassificationResult(BaseModel):
    """Output of a DocumentClassifier for a single document."""

    document_id: str
    document_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    matched_signals: list[str] = Field(default_factory=list)


class ExtractedField(BaseModel):
    """A single extracted metadata field with basic provenance."""

    name: str
    value: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ExtractedMetadata(BaseModel):
    """All metadata fields extracted from a single document."""

    document_id: str
    document_type: str
    fields: dict[str, ExtractedField] = Field(default_factory=dict)

    def as_plain_dict(self) -> dict[str, str]:
        """Return field values as a flat name -> value mapping."""
        return {name: field.value for name, field in self.fields.items()}


class ClassifiedDocument(BaseModel):
    """A document bundled with its classification and extracted metadata.

    This is the primary unit that question generators operate on.
    """

    document: Document
    classification: ClassificationResult
    metadata: ExtractedMetadata

    model_config = {"arbitrary_types_allowed": True}


class BenchmarkQuery(BaseModel):
    """A single generated benchmark question, matching benchmark_queries.json."""

    id: int
    query: str
    expected_document: str
    expected_fields: list[str] = Field(default_factory=list)
    document_type: str
    difficulty: Difficulty
    tags: list[str] = Field(default_factory=list)
    template_id: str


class BenchmarkDataset(BaseModel):
    """A full collection of benchmark queries plus generation provenance."""

    queries: list[BenchmarkQuery] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    template: str = "generic"
    source_dataset: Path | None = None

    model_config = {"arbitrary_types_allowed": True}


class RetrievalResult(BaseModel):
    """Result of running a single query against a RAG system (future use)."""

    query: str
    expected_document: str
    returned_document: str | None = None
    top_score: float | None = None
    success: bool = False
    rank: int | None = None


class LatencyResult(BaseModel):
    """Latency breakdown for a single query execution (future use)."""

    query: str
    retriever_ms: float = 0.0
    research_ms: float = 0.0
    summarizer_ms: float = 0.0
    citation_ms: float = 0.0
    total_ms: float = 0.0
    tokens: int = 0


class ValidationIssue(BaseModel):
    """A single problem found while validating a benchmark dataset."""

    severity: str  # "error" | "warning"
    code: str
    message: str
    query_id: int | None = None


class ValidationReport(BaseModel):
    """Aggregate result of validating a BenchmarkDataset."""

    issues: list[ValidationIssue] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(issue.severity == "error" for issue in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity == "warning")


class DatasetStatistics(BaseModel):
    """Aggregate statistics used to build the markdown report."""

    total_documents: int = 0
    document_type_counts: dict[str, int] = Field(default_factory=dict)
    total_questions: int = 0
    avg_questions_per_document: float = 0.0
    unknown_document_types: int = 0
    metadata_field_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

@dataclass(slots=True)
class GenerationStats:
    """
    Statistics for one processed document.
    """
    document_name: str
    document_type: str
    generated_questions: int = 0
    generated_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    available_fields: list[str] = field(default_factory=list)
    skipped_fields: list[str] = field(default_factory=list)
    generated_questions: int = 0
    max_possible_questions: int = 0

@dataclass(slots=True)
class QuestionGenerationResult:
    queries: list[BenchmarkQuery]
    statistics: list[GenerationStats]

@dataclass
class QuestionField:
    name: str
    required: bool = False
    aliases: list[str] = field(default_factory=list)
    weight: int = 1

@dataclass
class Summary:
    total_documents: int
    classified_documents: int
    extracted_fields: int
    total_fields: int
    generated_questions: int
    skipped_questions: int
    coverage: float







