"""Turns diagnostic facts and statistics into actionable recommendations.

This is the only module allowed to phrase advice as text — `analyzer.py`
and `statistics.py` stay purely descriptive so their output can be tested
without asserting on prose.
"""

from __future__ import annotations

from rag_benchmark.utils import get_logger
from rag_benchmark.diagnostics.models import (
    PipelineDiagnostics,
    ClassificationStats,
    DocumentTypeMetadataCoverage,
    QuestionTypeStats,
    Recommendation
)
logger = get_logger("diagnostics.recommendations")

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


def _unknown_document_recommendations(diagnostics: PipelineDiagnostics) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    seen_types: set[str] = set()

    for diag in diagnostics.unknown_diagnostics:
        rule = diag.suggested_rule
        if rule is None or rule.document_type in seen_types:
            continue
        seen_types.add(rule.document_type)

        content_hint = ", ".join(rule.content_patterns) if rule.content_patterns else "(none detected)"
        recommendations.append(
            Recommendation(
                context=rule.document_type,
                issue=f"No classification rule matches '{diag.classified.document.filename}'.",
                suggestion=(
                    f"Create document type '{rule.document_type}' — "
                    f"filename pattern: '{rule.filename_pattern}', "
                    f"content patterns: {content_hint}."
                ),
                severity=SEVERITY_WARNING,
            )
        )
        if len(recommendations) >= MAX_TEMPLATE_RECOMMENDATIONS:
            break

    return recommendations


def _metadata_recommendations(
    metadata_coverage: list[DocumentTypeMetadataCoverage],
) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for coverage in metadata_coverage:
        for field_coverage in coverage.fields:
            if field_coverage.coverage_percent == 0.0:
                recommendations.append(
                    Recommendation(
                        context=coverage.document_type,
                        issue=f"'{field_coverage.field_name}' missing in all documents.",
                        suggestion="Improve the regex pattern(s) for this field.",
                        severity=SEVERITY_CRITICAL,
                    )
                )
            elif field_coverage.coverage_percent < LOW_FIELD_COVERAGE_THRESHOLD:
                recommendations.append(
                    Recommendation(
                        context=coverage.document_type,
                        issue=(
                            f"'{field_coverage.field_name}' extracted in only "
                            f"{field_coverage.coverage_percent:.0f}% of documents."
                        ),
                        suggestion="Expand extraction rules to cover more phrasings.",
                        severity=SEVERITY_WARNING,
                    )
                )
    return recommendations


def _question_recommendations(question_stats: list[QuestionTypeStats]) -> list[Recommendation]:
    recommendations: list[Recommendation] = []
    for stats in question_stats:
        if stats.possible > 0 and stats.coverage_percent < LOW_QUESTION_COVERAGE_THRESHOLD:
            recommendations.append(
                Recommendation(
                    context=stats.document_type,
                    issue=(
                        f"Only {stats.coverage_percent:.0f}% of possible questions "
                        f"were generated ({stats.generated}/{stats.possible})."
                    ),
                    suggestion="Improve metadata extraction coverage to unlock more questions.",
                    severity=SEVERITY_WARNING,
                )
            )
    return recommendations


def generate_recommendations(
    diagnostics: PipelineDiagnostics,
    classification_stats: ClassificationStats,
    metadata_coverage: list[DocumentTypeMetadataCoverage],
    question_stats: list[QuestionTypeStats],
) -> list[Recommendation]:
    """Generate the full set of recommendations for a diagnostics run.

    Args:
        diagnostics: The pipeline diagnostics snapshot.
        classification_stats: Output of `compute_classification_stats`.
        metadata_coverage: Output of `compute_metadata_coverage`.
        question_stats: Output of `compute_question_stats`.

    Returns:
        All recommendations, critical severity first.
    """
    recommendations = (
        _unknown_document_recommendations(diagnostics)
        + _metadata_recommendations(metadata_coverage)
        + _question_recommendations(question_stats)
    )

    if classification_stats.unknown_count == 0 and not recommendations:
        logger.debug("No issues detected; dataset looks benchmark-ready.")

    severity_order = {SEVERITY_CRITICAL: 0, SEVERITY_WARNING: 1, SEVERITY_INFO: 2}
    recommendations.sort(key=lambda r: severity_order.get(r.severity, 99))
    logger.info("Generated %d recommendation(s)", len(recommendations))
    return recommendations