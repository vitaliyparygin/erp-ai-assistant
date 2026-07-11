"""Single-file inspection: everything the pipeline knows about one document.

Powers `rag-benchmark inspect FILE_NAME`. Kept separate from `analyzer.py`
because it answers a different question — not "how healthy is the whole
dataset" but "why did this one file end up the way it did" — and has a
different entry point (a filename, not a whole directory).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rag_benchmark.classifier import UNKNOWN_TYPE
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.diagnostics.analyzer import (
    TEXT_PREVIEW_CHARS,
    SuggestedClassificationRule,
    extract_keywords,
    suggest_classification_rule,
)
from rag_benchmark.extractor import RegexMetadataExtractor
from rag_benchmark.models import BenchmarkQuery, ClassifiedDocument, DocumentFormat, ScannedFile
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.scanner import detect_format
from rag_benchmark.utils import get_logger, truncate
from rag_benchmark.templates import TemplateDefinition
from rag_benchmark.diagnostics.models import (
    TemplateSuggestion,
    RegexSuggestion,
    RegexStat,
    RegexCandidate,
    ClassificationScore,
    MatchedKeyword,
    MetadataDetail,
    RegexCoverage,
    ReadinessReport,
    InspectSummary,
    GeneratedQuestion,
    QuestionCoverage,
    FieldCoverage
)
from rag_benchmark.generators.base import QuestionTemplateMap
logger = get_logger("diagnostics.inspect")


class DocumentNotFoundError(FileNotFoundError):
    """Raised when `inspect` cannot locate a file matching the given name."""


class UnsupportedDocumentError(ValueError):
    """Raised when the located file's format has no registered reader."""


@dataclass
class InspectResult:
    # Source
    scanned_file: ScannedFile
    classified: ClassifiedDocument

    question_templates: QuestionTemplateMap
    questions: list[GeneratedQuestion]

    # Metadata
    expected_fields: list[str]
    missing_fields: list[str]
    available_fields: list[str]

    text_preview: str

    # Filled by InspectAnalyzer
    classification_scores: list[ClassificationScore] = field(default_factory=list)
    matched_keywords: list[MatchedKeyword] = field(default_factory=list)

    metadata_details: list[MetadataDetail] = field(default_factory=list)
    field_coverage: FieldCoverage | None = None

    regex_stats: list[RegexStat] = field(default_factory=list)
    regex_coverage: RegexCoverage | None = None
    regex_candidates: list[RegexCandidate] = field(default_factory=list)
    regex_suggestions: list[RegexSuggestion] = field(default_factory=list)

    question_coverage: QuestionCoverage | None = None
    template_suggestions: list[TemplateSuggestion] = field(default_factory=list)

    readiness: ReadinessReport | None = None

    @property
    def is_unknown(self) -> bool:
        return self.classified.classification.document_type == UNKNOWN_TYPE


def find_document(dataset_dir: Path, name: str, recursive: bool = True) -> Path:
    """Locate a file within the dataset directory by name or stem.

    Matching is case-insensitive and tries, in order: an exact filename
    match, then a match on the filename stem (extension-agnostic), so
    `inspect "Vendor Profile"` and `inspect vendor_profile.txt` both work.

    Args:
        dataset_dir: Directory to search.
        name: Filename or stem to look for.
        recursive: Whether to search subdirectories.

    Returns:
        The matched file's path.

    Raises:
        DocumentNotFoundError: If no file matches.
    """
    pattern = "**/*" if recursive else "*"
    candidates = [p for p in Path(dataset_dir).glob(pattern) if p.is_file()]

    target_lower = name.lower()
    for candidate in candidates:
        if candidate.name.lower() == target_lower:
            return candidate
    for candidate in candidates:
        if candidate.stem.lower() == target_lower:
            return candidate

    raise DocumentNotFoundError(
        f"No file named '{name}' found under {dataset_dir} "
        f"(searched {len(candidates)} file(s))."
    )


def inspect_document(
    pipeline: BenchmarkPipeline,
    config: BenchmarkConfig,
    filename: str
) -> InspectResult:
    """Run a single document through the full pipeline and collect diagnostics.

    Args:
        pipeline: The pipeline instance to drive.
        config: Resolved benchmark configuration.
        filename: Filename or stem to locate within `config.dataset`.

    Returns:
        A fully populated InspectResult.

    Raises:
        DocumentNotFoundError: If no matching file is found.
        UnsupportedDocumentError: If the file's format has no reader.
    """
    path = find_document(config.dataset, filename, recursive=config.recursive)
    logger.debug("Resolved '%s' to %s", filename, path)

    fmt = detect_format(path)
    if fmt is DocumentFormat.UNKNOWN:
        raise UnsupportedDocumentError(f"'{path.name}' has an unsupported format for reading.")

    stat = path.stat()
    scanned = ScannedFile(
        path=path,
        format=fmt,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime),
    )

    template = pipeline.resolve_template(config)
    document = pipeline.readers.read(path, fmt)
    classifier = pipeline.build_classifier(template)
    extractor = pipeline.build_extractor(template)

    classification = classifier.classify(document)
    metadata = extractor.extract(document, classification.document_type)
    classified = ClassifiedDocument(
        document=document, classification=classification, metadata=metadata
    )
    # recommendations = generate_recommendations(
    #     #     diagnostics, classification, metadata, question_stats
    #     # )
    expected_fields = (
        extractor.expected_fields(classification.document_type)
        if isinstance(extractor, RegexMetadataExtractor)
        else []
    )
    available = set(metadata.fields.keys())
    missing_fields = [f for f in expected_fields if f not in available]

    questions = pipeline.generator.generate(
        documents=[classified],
        template_map=template.question_templates,
        max_questions_per_document=config.max_questions_per_document,
    )

    keywords: list[str] = []
    suggested_rule: SuggestedClassificationRule | None = None
    if classification.document_type == UNKNOWN_TYPE:
        keywords = extract_keywords(document.text)
        suggested_rule = suggest_classification_rule(document.filename, keywords)

    logger.info(
        "Inspected %s: type=%s, fields=%d/%d, questions=%d",
        document.filename,
        classification.document_type,
        len(available),
        len(expected_fields),
        len(questions),
    )

    return InspectResult(
        scanned_file=scanned,
        classified=classified,
        question_templates=template,
        questions=questions,
        expected_fields=expected_fields,
        missing_fields=missing_fields,
        available_fields=available,
        text_preview=truncate(document.text, TEXT_PREVIEW_CHARS),
    )