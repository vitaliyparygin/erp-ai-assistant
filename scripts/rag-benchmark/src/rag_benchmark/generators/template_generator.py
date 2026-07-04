"""Deterministic, template-driven question generation."""

from __future__ import annotations

from rag_benchmark.generators.base import QuestionGenerator, QuestionTemplateMap
from rag_benchmark.models import BenchmarkQuery, ClassifiedDocument
from rag_benchmark.utils import get_logger

logger = get_logger("generators.template")


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
        next_id = 1

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
            generated_for_doc = 0

            for spec in specs:
                if generated_for_doc >= max_questions_per_document:
                    break

                missing = [f for f in spec.requires_fields if f not in available_fields]
                if missing:
                    continue

                if spec.requires_fields:
                    # One question per required field, rendered individually.
                    for field_name in spec.requires_fields:
                        if generated_for_doc >= max_questions_per_document:
                            break
                        query_text = spec.query_template.format(
                            field=field_name.replace("_", " "),
                            filename=classified.document.filename,
                            **available_fields,
                        )
                        queries.append(
                            BenchmarkQuery(
                                id=next_id,
                                query=query_text,
                                expected_document=classified.document.filename,
                                expected_fields=[field_name],
                                document_type=doc_type,
                                difficulty=spec.difficulty,
                                tags=list(spec.tags),
                            )
                        )
                        next_id += 1
                        generated_for_doc += 1
                else:
                    query_text = spec.query_template.format(
                        filename=classified.document.filename, **available_fields
                    )
                    queries.append(
                        BenchmarkQuery(
                            id=next_id,
                            query=query_text,
                            expected_document=classified.document.filename,
                            expected_fields=[],
                            document_type=doc_type,
                            difficulty=spec.difficulty,
                            tags=list(spec.tags),
                        )
                    )
                    next_id += 1
                    generated_for_doc += 1

        logger.info("Generated %d question(s) from %d document(s)", len(queries), len(documents))
        return queries
