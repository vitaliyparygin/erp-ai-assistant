"""Deterministic, template-driven question generation."""

from __future__ import annotations

from rag_benchmark.generators.base import QuestionGenerator, QuestionTemplateMap
from rag_benchmark.models import (BenchmarkQuery,
                                  ClassifiedDocument,
                                  QuestionGenerationResult,
                                  GenerationStats)
from rag_benchmark.utils import get_logger
from rich.console import Console
logger = get_logger("generators.template")

console = Console()

class TemplateQuestionGenerator(QuestionGenerator):
    """Generates questions by filling QuestionSpec templates with metadata.

    For each document, applicable specs (those whose required fields were
    all extracted) are rendered into concrete queries, up to the configured
    per-document cap. Specs with no required fields always apply.
    """

    def generate(
        self,
        documents: list[ClassifiedDocument],
        template_map: QuestionTemplateMap,
        max_questions_per_document: int,
    ) -> list[BenchmarkQuery]:
        queries: list[BenchmarkQuery] = []
        stats: list[GenerationStats] = []
        next_id = 1

        console.print(
            f"[yellow]Generated[/yellow]"
        )
        for classified in documents:
            doc_type = classified.classification.document_type
            specs = template_map.get(doc_type, [])
            if not specs:
                logger.debug(
                    "No question specs for document_type=%s (%s)",
                    doc_type,
                    classified.document.filename,
                )
                continue

            available_fields = classified.metadata.as_plain_dict()
            doc_stats = GenerationStats(
                document_name=classified.document.filename,
                document_type=doc_type,
            )
            generated_for_doc = 0
            logger.debug(f"generate.specs specs={specs} max_questions_per_document={max_questions_per_document}")
            for spec in specs:
                if generated_for_doc >= max_questions_per_document:
                    logger.debug(f"generated_for_doc >= max_questions_per_document1"
                          f"generated_for_doc={generated_for_doc} max_questions_per_document={max_questions_per_document}")
                    break

                for field in spec.fields:

                    if generated_for_doc >= max_questions_per_document:
                        break

                    if field.name not in available_fields:
                        if field.required:
                            doc_stats.missing_fields.append(field.name)
                        continue

                    display_name = (
                        field.aliases[0]
                        if field.aliases
                        else field.name.replace("_", " ")
                    )
                    query_text = spec.query_template.format(
                        field=display_name,
                        filename=classified.document.filename,
                        **available_fields,
                    )

                    queries.append(
                        BenchmarkQuery(
                            id=next_id,
                            query=query_text,
                            expected_document=classified.document.filename,
                            expected_fields=[field.name],
                            document_type=doc_type,
                            difficulty=spec.difficulty,
                            tags=list(spec.tags),
                        )
                    )
                    doc_stats.generated_questions += 1
                    doc_stats.generated_fields.append(field.name)

                    next_id += 1
                    generated_for_doc += 1

                stats.append(doc_stats)
                logger.debug(
                    "Document=%s generated=%d generated_fields=%s missing=%s",
                    doc_stats.document_name,
                    doc_stats.generated_questions,
                    doc_stats.generated_fields,
                    doc_stats.missing_fields,
                )
        # return queries
        return queries