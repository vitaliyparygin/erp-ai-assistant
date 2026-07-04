"""Abstract question generator interface and the template data contract.

A "template" in this package (see rag_benchmark.templates) is simply a
mapping of document_type -> list[QuestionSpec]. Generators consume that
mapping to produce BenchmarkQuery objects; they never contain domain
knowledge themselves, which is what keeps the core package framework
(and domain) agnostic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from rag_benchmark.models import BenchmarkQuery, ClassifiedDocument, Difficulty


@dataclass(frozen=True)
class QuestionSpec:
    """A single question pattern belonging to a template.

    Attributes:
        query_template: A format string, e.g. "What is the {field} of
            {filename}?". May reference `{field}` (a specific metadata
            field name declared in `requires_fields`) and `{filename}`.
        requires_fields: Metadata field names that must be present on the
            document for this spec to apply. If empty, the spec applies
            regardless of extracted metadata.
        difficulty: Difficulty tier assigned to generated questions.
        tags: Tags attached to generated questions.
    """

    query_template: str
    requires_fields: tuple[str, ...] = field(default_factory=tuple)
    difficulty: Difficulty = Difficulty.EASY
    tags: tuple[str, ...] = field(default_factory=tuple)


# document_type -> question specs for that type.
QuestionTemplateMap = dict[str, list[QuestionSpec]]


class QuestionGenerator(ABC):
    """Abstract interface for turning classified documents into questions."""

    @abstractmethod
    def generate(
        self,
        documents: list[ClassifiedDocument],
        template_map: QuestionTemplateMap,
        max_questions_per_document: int,
    ) -> list[BenchmarkQuery]:
        """Generate benchmark questions for a set of classified documents.

        Args:
            documents: Documents with classification and metadata already
                populated.
            template_map: document_type -> QuestionSpec list, typically
                sourced from a template plugin.
            max_questions_per_document: Upper bound on questions generated
                per document.

        Returns:
            A flat list of BenchmarkQuery objects with sequential ids.
        """
        raise NotImplementedError
