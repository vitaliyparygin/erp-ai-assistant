"""Benchmark diagnostics subsystem.

Public entry point: `build_diagnostics_report`, which runs the pipeline in
read-only mode and returns a fully-computed `DiagnosticsReport` — the
single object `reporter.py` needs to render everything from Rich console
output to the `diagnose_latest.md` export.
"""

from __future__ import annotations

from dataclasses import dataclass
from rag_benchmark.analyzers.question_generation import QuestionGenerationAnalyzer
from rag_benchmark.analyzers.question_coverage import (QuestionCoverageAnalyzer)
from rag_benchmark.analyzers.question_template_analyzer import QuestionTemplateAnalyzer
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.diagnostics.analyzer import PipelineDiagnostics, run_diagnostics
from rag_benchmark.diagnostics.recommendations import Recommendation, generate_recommendations
from rag_benchmark.diagnostics.statistics import (
    ClassificationStats,
    DocumentTypeMetadataCoverage,
    QuestionTypeStats,
    ReadinessScores,
    compute_classification_stats,
    compute_metadata_coverage,
    compute_question_stats,
    compute_readiness,
)
from rag_benchmark.pipeline import BenchmarkPipeline
from rag_benchmark.utils import get_logger

logger = get_logger("diagnostics")


@dataclass
class DiagnosticsReport:
    """Everything a diagnostics report needs to render, in one object."""

    pipeline_diagnostics: PipelineDiagnostics
    classification: ClassificationStats
    metadata_coverage: list[DocumentTypeMetadataCoverage]
    question_stats: list[QuestionTypeStats]
    readiness: ReadinessScores
    recommendations: list[Recommendation]


def build_diagnostics_report(
    pipeline: BenchmarkPipeline,
    config: BenchmarkConfig,
    file: str | None = None,
) -> DiagnosticsReport:
    """Run the pipeline read-only and compute the full diagnostics report.

    Args:
        pipeline: The pipeline instance to drive.
        config: Resolved benchmark configuration.

    Returns:
        A complete DiagnosticsReport.
    """
    logger.info("Starting diagnostics run for dataset: %s", config.dataset)
    diagnostics = run_diagnostics(pipeline, config, file)

    classification = compute_classification_stats(diagnostics)
    metadata_coverage = compute_metadata_coverage(diagnostics)
    question_stats = compute_question_stats(diagnostics)
    readiness = compute_readiness(classification, metadata_coverage, question_stats)
    recommendations = generate_recommendations(
        diagnostics, classification, metadata_coverage, question_stats
    )
    QuestionGenerationAnalyzer.report(
        diagnostics.document_diagnostics,
    )

    QuestionCoverageAnalyzer.report(
        diagnostics.document_diagnostics,
    )

    QuestionTemplateAnalyzer.report(
        diagnostics.document_diagnostics,
        diagnostics.template,
    )

    logger.info("Diagnostics complete: overall readiness %.1f%%", readiness.overall_score)
    return DiagnosticsReport(
        pipeline_diagnostics=diagnostics,
        classification=classification,
        metadata_coverage=metadata_coverage,
        question_stats=question_stats,
        readiness=readiness,
        recommendations=recommendations,
    )


__all__ = ["DiagnosticsReport", "build_diagnostics_report"]