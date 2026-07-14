"""Statistical computations over a PipelineDiagnostics snapshot.

Every function here is a pure function: facts in, numbers out. No Rich, no
I/O, no recommendation text — that separation is what keeps this module
trivially testable.
"""

from __future__ import annotations

from rag_benchmark.classifier import UNKNOWN_TYPE
from rag_benchmark.logging import get_logger
from rag_benchmark.diagnostics.models import (
    PipelineDiagnostics,
    DocumentDiagnostic,
    ClassificationStats,
    DocumentTypeMetadataCoverage,
    QuestionTypeStats,
    ReadinessScores,
    FieldCoverage
)

logger = get_logger("diagnostics.statistics")

#: Readiness score thresholds (percent) used to bucket the overall status.
READINESS_EXCELLENT_THRESHOLD = 90.0
READINESS_GOOD_THRESHOLD = 75.0
READINESS_FAIR_THRESHOLD = 50.0

STATUS_EXCELLENT = "Excellent"
STATUS_GOOD = "Good"
STATUS_FAIR = "Fair"
STATUS_POOR = "Poor"


def _percent(numerator: float, denominator: float) -> float:
    """Return numerator/denominator as a percentage, or 0.0 if denominator is 0."""
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


def _mean(values: list[float]) -> float:
    """Return the mean of a list of values, or 0.0 for an empty list."""
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)

def compute_classification_stats(diagnostics: PipelineDiagnostics) -> ClassificationStats:
    """Tally how many documents landed in each document type.

    Args:
        diagnostics: A completed pipeline diagnostics snapshot.

    Returns:
        Aggregate classification counts and rate.
    """
    counts: dict[str, int] = {}
    for classified in diagnostics.classified_documents:
        doc_type = classified.classification.document_type
        counts[doc_type] = counts.get(doc_type, 0) + 1

    total = len(diagnostics.classified_documents)
    unknown = counts.get(UNKNOWN_TYPE, 0)
    classified_count = total - unknown

    stats = ClassificationStats(
        counts=counts,
        total_documents=total,
        classified_count=classified_count,
        unknown_count=unknown,
        classification_rate=_percent(classified_count, total),
    )
    logger.debug(
        "Classification stats: %d/%d classified (%.1f%%)",
        classified_count,
        total,
        stats.classification_rate,
    )
    return stats


def _group_by_document_type(
    diagnostics: PipelineDiagnostics, *, exclude_unknown: bool
) -> dict[str, list[DocumentDiagnostic]]:
    grouped: dict[str, list[DocumentDiagnostic]] = {}
    for diag in diagnostics.document_diagnostics:
        if exclude_unknown and diag.is_unknown:
            continue
        grouped.setdefault(diag.document_type, []).append(diag)
    return grouped


def compute_metadata_coverage(
    diagnostics: PipelineDiagnostics,
) -> list[DocumentTypeMetadataCoverage]:
    """Compute per-field extraction coverage for every classified document type.

    Unknown documents are excluded since they have no expected fields to
    measure against.

    Args:
        diagnostics: A completed pipeline diagnostics snapshot.

    Returns:
        One DocumentTypeMetadataCoverage per document type that has at
        least one expected field, sorted by document type name.
    """
    grouped = _group_by_document_type(diagnostics, exclude_unknown=True)
    results: list[DocumentTypeMetadataCoverage] = []

    for doc_type, diags in sorted(grouped.items()):
        expected_fields = diags[0].extracted_fields
        if not expected_fields:
            continue

        field_coverages: list[FieldCoverage] = []
        for field_name in expected_fields:
            with_field = sum(1 for d in diags if field_name in d.extracted_fields)
            field_coverages.append(
                FieldCoverage(
                    field_name=field_name,
                    documents_with_field=with_field,
                    total_documents_of_type=len(diags),
                    coverage_percent=_percent(with_field, len(diags)),
                )
            )

        overall = _mean([fc.coverage_percent for fc in field_coverages])
        results.append(
            DocumentTypeMetadataCoverage(
                document_type=doc_type,
                fields=field_coverages,
                overall_coverage_percent=overall,
            )
        )

    return results


def compute_question_stats(diagnostics: PipelineDiagnostics) -> list[QuestionTypeStats]:
    """Compute possible vs. generated questions for every document type
    that the active template defines question specs for.

    "Possible" assumes every expected field had been extracted (one
    question per required field per spec, or one per spec with no
    required fields) — it is the ceiling `generated` could reach if
    extraction were perfect.

    Args:
        diagnostics: A completed pipeline diagnostics snapshot.

    Returns:
        One QuestionTypeStats per in-scope document type, sorted by name.
    """
    grouped = _group_by_document_type(diagnostics, exclude_unknown=False)
    template_map = diagnostics.template.question_templates
    results: list[QuestionTypeStats] = []

    for doc_type, diags in sorted(grouped.items()):
        specs = template_map.get(doc_type, [])
        if not specs:
            continue

        possible_per_document = sum(len(spec.fields) or 1 for spec in specs)
        possible = possible_per_document * len(diags)
        generated = sum(
            d.question_generation.generated
            if d.question_generation
            else 0
            for d in diags
        )
        skipped = sum(
            d.question_generation.skipped
            if d.question_generation
            else 0
            for d in diags
        )

        results.append(
            QuestionTypeStats(
                document_type=doc_type,
                possible=possible,
                generated=generated,
                skipped=skipped,
                coverage_percent=_percent(generated, possible),
            )
        )

    return results


def _status_for_score(score: float) -> str:
    if score >= READINESS_EXCELLENT_THRESHOLD:
        return STATUS_EXCELLENT
    if score >= READINESS_GOOD_THRESHOLD:
        return STATUS_GOOD
    if score >= READINESS_FAIR_THRESHOLD:
        return STATUS_FAIR
    return STATUS_POOR


def compute_readiness(
    classification_stats: ClassificationStats,
    metadata_coverage: list[DocumentTypeMetadataCoverage],
    question_stats: list[QuestionTypeStats],
) -> ReadinessScores:
    """Roll every stage's stats up into a single readiness verdict.

    Each of the three stage scores is weighted equally in the overall
    score; this is a deliberately simple, transparent default rather than
    a tuned formula, since developers reading `diagnose` output need to be
    able to reconstruct the number in their head.

    Args:
        classification_stats: Output of `compute_classification_stats`.
        metadata_coverage: Output of `compute_metadata_coverage`.
        question_stats: Output of `compute_question_stats`.

    Returns:
        Final ReadinessScores including a human-readable status label.
    """
    classification_score = classification_stats.classification_rate
    extraction_score = _mean([c.overall_coverage_percent for c in metadata_coverage])
    question_score = _mean([q.coverage_percent for q in question_stats])
    overall_score = _mean([classification_score, extraction_score, question_score])

    scores = ReadinessScores(
        classification_score=classification_score,
        extraction_score=extraction_score,
        question_score=question_score,
        overall_score=overall_score,
        status=_status_for_score(overall_score),
    )
    logger.debug("Readiness scores: %s", scores)
    return scores