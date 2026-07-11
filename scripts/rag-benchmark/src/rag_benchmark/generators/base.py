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

from rag_benchmark.models import BenchmarkQuery, ClassifiedDocument, Difficulty, QuestionField


@dataclass(frozen=True)
class QuestionSpec:
    """
    Template describing one family of questions.
    """
    key: str
    query_template: str
    fields: tuple[QuestionField, ...]
    difficulty: Difficulty = Difficulty.EASY
    tags: tuple[str, ...] = ()
    max_questions: int | None = None


# document_type -> question specs for that type.
QuestionTemplateMap = dict[str, list[QuestionSpec]]

TemplateRegistry = QuestionTemplateMap

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
