"""Pipeline analysis: runs the full pipeline without writing any artifacts
and builds per-document diagnostic data (missing fields, keywords for
unclassified documents, classification-rule suggestions).

This module answers "what happened at each stage", staying strictly
descriptive. Turning those facts into percentages lives in `statistics.py`;
turning them into actionable advice lives in `recommendations.py`.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import rag_benchmark
from rag_benchmark.classifier import UNKNOWN_TYPE
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.extractor import RegexMetadataExtractor
from rag_benchmark.models import BenchmarkDataset, BenchmarkQuery, ClassifiedDocument
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.templates import TemplateDefinition
from rag_benchmark.utils import get_logger, normalize_whitespace, slugify

from rag_benchmark.analyzers.regex_analyzer import RegexAnalyzer
from rag_benchmark.analyzers.field_coverage import FieldCoverageAnalyzer
from rag_benchmark.analyzers.question_coverage import QuestionCoverageAnalyzer
from rag_benchmark.analyzers.document_summary import DocumentSummaryAnalyzer

logger = get_logger("diagnostics.analyzer")

#: Default number of candidate keywords surfaced per unclassified document.
DEFAULT_MAX_KEYWORDS = 5

#: Default number of keywords promoted into a suggested content pattern.
DEFAULT_MAX_CONTENT_PATTERNS = 3

#: How many characters of raw text to keep for the `inspect` text preview.
TEXT_PREVIEW_CHARS = 600

_LABEL_PATTERN = re.compile(
    r"(?m)^[ \t]*([A-Z][A-Za-z]{1,24}(?:\s[A-Z][A-Za-z]{1,24}){0,3})\s*[:\-]"
)


def extract_keywords(text: str, max_keywords: int = DEFAULT_MAX_KEYWORDS) -> list[str]:
    """Extract candidate field-label keywords from unstructured document text.

    Looks for "Label: value" / "Label - value" style lines, which are a
    strong signal of what a document is about even when no classification
    rule recognizes it yet.

    Args:
        text: Raw document text.
        max_keywords: Maximum number of keywords to return, most frequent
            first.

    Returns:
        A list of distinct labels, most frequent first.
    """
    counts: Counter[str] = Counter()
    for match in _LABEL_PATTERN.finditer(text):
        label = normalize_whitespace(match.group(1))
        counts[label] += 1
    return [label for label, _ in counts.most_common(max_keywords)]


@dataclass(frozen=True)
class SuggestedClassificationRule:
    """A human-readable suggestion for classifying a currently-unknown document."""

    document_type: str
    filename_pattern: str
    content_patterns: list[str]


def suggest_classification_rule(
    filename: str,
    keywords: list[str],
    max_content_patterns: int = DEFAULT_MAX_CONTENT_PATTERNS,
) -> SuggestedClassificationRule:
    """Infer a plausible new classification rule for an unclassified document.

    Args:
        filename: The document's filename (used to guess a type name and
            filename pattern).
        keywords: Candidate keywords already extracted from the document's
            content (see `extract_keywords`).
        max_content_patterns: How many keywords to promote into suggested
            content patterns.

    Returns:
        A SuggestedClassificationRule ready to display or turn into a
        template snippet.
    """
    stem = Path(filename).stem
    words = [w for w in re.split(r"[_\-\s]+", stem) if w]
    name_words = [w for w in words if not w.isdigit()] or words
    document_type = " ".join(w.capitalize() for w in name_words) if name_words else stem
    filename_pattern = slugify(" ".join(name_words)).replace("-", " ") if name_words else stem.lower()
    content_patterns = [kw.lower() for kw in keywords[:max_content_patterns]]
    return SuggestedClassificationRule(
        document_type=document_type,
        filename_pattern=filename_pattern,
        content_patterns=content_patterns,
    )


@dataclass
class DocumentDiagnostic:
    """Per-document diagnostic facts, combining every pipeline stage's output."""

    classified: ClassifiedDocument
    expected_fields: list[str]
    missing_fields: list[str]
    questions: list[BenchmarkQuery] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    suggested_rule: SuggestedClassificationRule | None = None

    @property
    def is_unknown(self) -> bool:
        return self.classified.classification.document_type == UNKNOWN_TYPE

    @property
    def available_fields(self) -> list[str]:
        return list(self.classified.metadata.fields.keys())


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


def run_diagnostics(pipeline: BenchmarkPipeline, config: BenchmarkConfig) -> PipelineDiagnostics:
    """Run the full pipeline in read-only mode and collect diagnostic data.

    This never calls any writer — it is safe to run repeatedly against a
    dataset without touching `benchmark_queries.json` or any other output
    artifact.

    Args:
        pipeline: The pipeline instance to drive (reused so injected
            collaborators, e.g. in tests, are respected).
        config: Resolved benchmark configuration.

    Returns:
        A PipelineDiagnostics snapshot covering every document.
    """
    logger.debug("Resolving template: %s", config.template)
    template = pipeline.resolve_template(config)

    logger.debug("Scanning dataset: %s", config.dataset)
    scanned_files = pipeline.load_documents(config.dataset, recursive=config.recursive)
    logger.info("Diagnostics: %d file(s) discovered", len(scanned_files))

    logger.debug("Classifying and extracting metadata for %d file(s)", len(scanned_files))
    classified_documents = pipeline.classify_and_extract(scanned_files, template)
    logger.info("Diagnostics: %d document(s) read successfully", len(classified_documents))

    logger.debug("Generating candidate questions")
    dataset = pipeline.generate(
        classified_documents, template, config.max_questions_per_document
    )
    dataset.source_dataset = config.dataset
    logger.info("Diagnostics: %d question(s) generated", len(dataset.queries))

    extractor = pipeline.build_extractor(template)
    questions_by_document: dict[str, list[BenchmarkQuery]] = defaultdict(list)
    for query in dataset.queries:
        questions_by_document[query.expected_document].append(query)

    document_diagnostics: list[DocumentDiagnostic] = []
    for classified in classified_documents:
        expected_fields = extractor.expected_fields(
            classified.classification.document_type
        )

        field_result = FieldCoverageAnalyzer.analyze(
            classified,
            expected_fields,
        )

        regex_result = RegexAnalyzer.analyze(
            classified,
            template,
        )

        question_result = QuestionCoverageAnalyzer.analyze(
            expected_fields,
            questions_by_document.get(
                classified.document.filename,
                [],
            ),
        )

        summary = DocumentSummaryAnalyzer.analyze(
            classified,
            field_result,
            regex_result,
            question_result,
        )

        document_diagnostics.append(summary)
    # for classified in classified_documents:
    #     doc_type = classified.classification.document_type
    #     expected_fields = (
    #         extractor.expected_fields(doc_type)
    #         if isinstance(extractor, RegexMetadataExtractor)
    #         else []
    #     )
    #     available = set(classified.metadata.fields.keys())
    #     missing_fields = [f for f in expected_fields if f not in available]
    #
    #     keywords: list[str] = []
    #     suggested_rule: SuggestedClassificationRule | None = None
    #     if doc_type == UNKNOWN_TYPE:
    #         keywords = extract_keywords(classified.document.text)
    #         suggested_rule = suggest_classification_rule(classified.document.filename, keywords)
    #         logger.debug(
    #             "Unknown document %s: suggested type=%s",
    #             classified.document.filename,
    #             suggested_rule.document_type,
    #         )
    #
    #     document_diagnostics.append(
    #         DocumentDiagnostic(
    #             classified=classified,
    #             expected_fields=expected_fields,
    #             missing_fields=missing_fields,
    #             questions=questions_by_document.get(classified.document.filename, []),
    #             keywords=keywords,
    #             suggested_rule=suggested_rule,
    #         )
    #     )

    return PipelineDiagnostics(
        config=config,
        template=template,
        classified_documents=classified_documents,
        dataset=dataset,
        document_diagnostics=document_diagnostics,
    )