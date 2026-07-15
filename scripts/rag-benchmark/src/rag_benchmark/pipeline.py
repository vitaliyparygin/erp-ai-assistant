"""High-level orchestration wiring scanner, reader, classifier, extractor,
and generator together.

This module contains no business logic of its own — it only composes the
single-responsibility components from the rest of the package via
dependency injection, so the CLI (and any other entry point, e.g. a
notebook or another package) can drive the whole pipeline with one call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rag_benchmark.classifier import DefaultClassifier, DocumentClassifier
from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.extractor import MetadataExtractor, RegexMetadataExtractor
from rag_benchmark.generators.base import QuestionGenerator
from rag_benchmark.generators.template_generator import TemplateQuestionGenerator
from rag_benchmark.models import (
    BenchmarkDataset,
    ClassifiedDocument,
    ScannedFile,
)
from rag_benchmark.pipeline_models import PipelineResult
from rag_benchmark.pdf_reader import ReaderRegistry
from rag_benchmark.scanner import DocumentScanner
from rag_benchmark.templates import TemplateDefinition, load_template
from rag_benchmark.logging import get_logger

logger = get_logger("pipeline")


@dataclass
class BenchmarkPipeline:
    """Coordinates the full scan -> read -> classify -> extract -> generate flow.

    All collaborators are injected with sensible defaults, so tests can
    substitute fakes for any stage without touching the others.
    """

    scanner: DocumentScanner | None = None
    readers: ReaderRegistry = field(default_factory=ReaderRegistry)
    classifier: DocumentClassifier | None = None
    extractor: MetadataExtractor | None = None
    generator: QuestionGenerator = field(default_factory=TemplateQuestionGenerator)

    def _resolve_template(self, config: BenchmarkConfig) -> TemplateDefinition:
        """Load the template referenced by a config.

        Exposed as its own method (rather than inlined in `run`) so other
        callers — notably the diagnostics subsystem — can resolve the same
        template `run()` would use without duplicating `load_template`
        calls or re-running the whole pipeline.
        """
        return load_template(config.template)

    def _build_classifier(self, template: TemplateDefinition) -> DocumentClassifier:
        """Return the classifier that would be used for a given template."""
        return self.classifier or DefaultClassifier(rules=template.classification_rules or None)

    def _build_extractor(self, template: TemplateDefinition) -> MetadataExtractor:
        """Return the extractor that would be used for a given template."""
        return self.extractor or RegexMetadataExtractor(
            extra_rules=template.extraction_rules or None
        )

    def scan(self, dataset_dir: Path, recursive: bool = True) -> list[ScannedFile]:
        """Scan a dataset directory for supported files.

        Args:
            dataset_dir: Directory to scan.
            recursive: Used only when no scanner was explicitly injected;
                an injected scanner's own configuration always wins.
        """
        scanner = self.scanner or DocumentScanner(recursive=recursive)
        return scanner.scan(dataset_dir)

    def classify(
        self, scanned_files: list[ScannedFile], template: TemplateDefinition
    ) -> list[ClassifiedDocument]:
        """Read, classify, and extract metadata for every scanned file.

        Args:
            scanned_files: Files discovered by the scanner.
            template: Resolved template supplying classification/extraction
                rule overrides.

        Returns:
            One ClassifiedDocument per successfully-read file. Files that
            fail to read are logged and skipped rather than aborting the
            whole run.
        """
        classifier = self._build_classifier(template)
        extractor = self._build_extractor(template)

        results: list[ClassifiedDocument] = []
        for scanned in scanned_files:
            try:
                document = self.readers.read(scanned.path, scanned.format)
            except (ValueError, RuntimeError) as exc:
                logger.warning("Skipping unreadable file %s: %s", scanned.path, exc)
                continue

            classification = classifier.classify(document)
            metadata = extractor.extract(document, classification.document_type)
            results.append(
                ClassifiedDocument(
                    document=document, classification=classification, metadata=metadata
                )
            )
        return results

    def generate(
        self,
        classified_documents: list[ClassifiedDocument],
        template: TemplateDefinition,
        max_questions_per_document: int,
    ) -> BenchmarkDataset:
        """Generate a BenchmarkDataset from classified documents."""
        queries = self.generator.generate(
            documents=classified_documents,
            template_map=template.question_templates,
            max_questions_per_document=max_questions_per_document,
        )
        return BenchmarkDataset(queries=queries, template=template.name)

    # def run(self, config: BenchmarkConfig) -> tuple[list[ClassifiedDocument], BenchmarkDataset, TemplateDefinition]:
    #     """Run the full pipeline end-to-end for a given configuration.
    #
    #     Returns:
    #         A tuple of (classified_documents, benchmark_dataset) so callers
    #         (e.g. the CLI's `report` command) can compute statistics without
    #         re-running the pipeline.
    #     """
    #     template = self._resolve_template(config)
    #     scanned_files = self.scan(config.dataset, recursive=config.recursive)
    #     classified_documents = self.classify(scanned_files, template)
    #     dataset = self.generate(
    #         classified_documents, template, config.max_questions_per_document
    #     )
    #     dataset.source_dataset = config.dataset
    #     return classified_documents, dataset, template

    def run(self, config: BenchmarkConfig):
        result = self.execute(config)

        return (
            result.classified_documents,
            result.dataset,
            result.template,
        )


    def execute(self, config: BenchmarkConfig) -> PipelineResult:
        template = self._resolve_template(config)

        scanned_files = self.scan(
            config.dataset,
            recursive=config.recursive,
        )

        classified = self.classify(
            scanned_files,
            template,
        )

        dataset = self.generate(
            classified,
            template,
            config.max_questions_per_document,
        )

        dataset.source_dataset = config.dataset

        return PipelineResult(
            config=config,
            template=template,
            scanned_files=scanned_files,
            classified_documents=classified,
            dataset=dataset,
        )