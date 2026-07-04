"""Statistics computation and validation for generated benchmark datasets."""

from __future__ import annotations

from collections import Counter

from rag_benchmark.classifier import UNKNOWN_TYPE
from rag_benchmark.models import (
    BenchmarkDataset,
    ClassifiedDocument,
    DatasetStatistics,
    ValidationIssue,
    ValidationReport,
)
from rag_benchmark.utils import get_logger

logger = get_logger("metrics")


def compute_statistics(
    classified_documents: list[ClassifiedDocument],
    dataset: BenchmarkDataset,
) -> DatasetStatistics:
    """Compute aggregate statistics for a report from pipeline outputs.

    Args:
        classified_documents: All documents that went through classification
            and extraction.
        dataset: The generated benchmark dataset.

    Returns:
        A populated DatasetStatistics instance.
    """
    doc_type_counts = Counter(
        cd.classification.document_type for cd in classified_documents
    )
    unknown_count = doc_type_counts.get(UNKNOWN_TYPE, 0)

    field_counts: Counter[str] = Counter()
    for cd in classified_documents:
        field_counts.update(cd.metadata.fields.keys())

    total_documents = len(classified_documents)
    total_questions = len(dataset.queries)
    avg_questions = (total_questions / total_documents) if total_documents else 0.0

    warnings: list[str] = []
    if unknown_count:
        warnings.append(f"{unknown_count} document(s) could not be classified.")
    documents_without_questions = total_documents - len(
        {q.expected_document for q in dataset.queries}
    )
    if documents_without_questions > 0:
        warnings.append(
            f"{documents_without_questions} document(s) produced no benchmark questions."
        )

    return DatasetStatistics(
        total_documents=total_documents,
        document_type_counts=dict(doc_type_counts),
        total_questions=total_questions,
        avg_questions_per_document=round(avg_questions, 3),
        unknown_document_types=unknown_count,
        metadata_field_counts=dict(field_counts),
        warnings=warnings,
    )


def validate_dataset(
    dataset: BenchmarkDataset,
    classified_documents: list[ClassifiedDocument] | None = None,
) -> ValidationReport:
    """Validate a benchmark dataset for structural and semantic issues.

    Checks performed:
        * duplicate question ids
        * duplicate (query, expected_document) pairs
        * missing expected_document (empty string)
        * expected_fields referencing metadata that was never extracted
          (only checked if classified_documents is provided)

    Args:
        dataset: The dataset to validate.
        classified_documents: Optional source documents, used to cross-check
            that expected_fields were actually extracted.

    Returns:
        A ValidationReport listing every issue found.
    """
    issues: list[ValidationIssue] = []

    seen_ids: set[int] = set()
    seen_query_doc_pairs: set[tuple[str, str]] = set()

    metadata_by_filename: dict[str, set[str]] = {}
    if classified_documents:
        for cd in classified_documents:
            metadata_by_filename[cd.document.filename] = set(cd.metadata.fields.keys())

    for query in dataset.queries:
        if query.id in seen_ids:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="duplicate_id",
                    message=f"Duplicate query id: {query.id}",
                    query_id=query.id,
                )
            )
        seen_ids.add(query.id)

        pair = (query.query.strip().lower(), query.expected_document)
        if pair in seen_query_doc_pairs:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="duplicate_question",
                    message=f"Duplicate question for {query.expected_document}: {query.query!r}",
                    query_id=query.id,
                )
            )
        seen_query_doc_pairs.add(pair)

        if not query.expected_document.strip():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="missing_expected_document",
                    message=f"Query {query.id} has no expected_document",
                    query_id=query.id,
                )
            )

        if not query.query.strip():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="invalid_metadata",
                    message=f"Query {query.id} has an empty query string",
                    query_id=query.id,
                )
            )

        if metadata_by_filename and query.expected_document in metadata_by_filename:
            available = metadata_by_filename[query.expected_document]
            missing = [f for f in query.expected_fields if f not in available]
            if missing:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="missing_extracted_fields",
                        message=(
                            f"Query {query.id} expects fields {missing} not extracted "
                            f"from {query.expected_document}"
                        ),
                        query_id=query.id,
                    )
                )

    report = ValidationReport(issues=issues)
    logger.info(
        "Validation complete: %d error(s), %d warning(s)",
        report.error_count,
        report.warning_count,
    )
    return report
