"""Tests for rag_benchmark.generators."""

from __future__ import annotations

import json
from pathlib import Path

from rag_benchmark.generators.base import QuestionSpec
from rag_benchmark.generators.llm_generator import LLMQuestionGenerator
from rag_benchmark.generators.template_generator import TemplateQuestionGenerator
from rag_benchmark.models import (
    ClassificationResult,
    ClassifiedDocument,
    Difficulty,
    Document,
    DocumentFormat,
    ExtractedField,
    ExtractedMetadata,
)


def _classified_invoice() -> ClassifiedDocument:
    document = Document(
        id="doc1",
        path=Path("invoice_001.txt"),
        filename="invoice_001.txt",
        format=DocumentFormat.TXT,
        text="Invoice Number: INV-1\nTotal Due: $1.00\n",
        char_count=10,
    )
    classification = ClassificationResult(
        document_id="doc1", document_type="Invoice", confidence=0.9, matched_signals=["x"]
    )
    metadata = ExtractedMetadata(
        document_id="doc1",
        document_type="Invoice",
        fields={
            "invoice_number": ExtractedField(name="invoice_number", value="INV-1"),
            "amount": ExtractedField(name="amount", value="1.00"),
        },
    )
    return ClassifiedDocument(document=document, classification=classification, metadata=metadata)


def test_template_generator_skips_spec_when_any_required_field_missing() -> None:
    template_map = {
        "Invoice": [
            QuestionSpec(
                "What is the {field} on {filename}?",
                requires_fields=("invoice_number", "amount", "customer"),
                difficulty=Difficulty.EASY,
                tags=("retrieval",),
            )
        ]
    }
    generator = TemplateQuestionGenerator()
    queries = generator.generate([_classified_invoice()], template_map, max_questions_per_document=10)

    # "customer" was never extracted, so the whole spec (all-or-nothing on
    # required fields) should be skipped, and no question generated for it.
    assert queries == []


def test_template_generator_generates_when_all_required_fields_present() -> None:
    template_map = {
        "Invoice": [
            QuestionSpec(
                "What is the {field} on {filename}?",
                requires_fields=("invoice_number", "amount"),
                difficulty=Difficulty.EASY,
                tags=("retrieval",),
            )
        ]
    }
    generator = TemplateQuestionGenerator()
    queries = generator.generate([_classified_invoice()], template_map, max_questions_per_document=10)

    assert len(queries) == 2
    assert {q.expected_fields[0] for q in queries} == {"invoice_number", "amount"}
    assert all(q.expected_document == "invoice_001.txt" for q in queries)
    assert [q.id for q in queries] == [1, 2]


def test_template_generator_respects_max_questions_per_document() -> None:
    template_map = {
        "Invoice": [
            QuestionSpec(
                "What is the {field} on {filename}?",
                requires_fields=("invoice_number", "amount"),
                difficulty=Difficulty.EASY,
            )
        ]
    }
    generator = TemplateQuestionGenerator()
    queries = generator.generate([_classified_invoice()], template_map, max_questions_per_document=1)
    assert len(queries) == 1


def test_template_generator_skips_document_type_not_in_template_map() -> None:
    generator = TemplateQuestionGenerator()
    queries = generator.generate([_classified_invoice()], {}, max_questions_per_document=5)
    assert queries == []


class _FakeLLMClient:
    def __init__(self, response: str) -> None:
        self._response = response

    def complete(self, system: str, user: str) -> str:  # noqa: ARG002
        return self._response


def test_llm_generator_parses_valid_json_response() -> None:
    response = json.dumps(
        [
            {
                "query": "What is the invoice number?",
                "expected_fields": ["invoice_number"],
                "difficulty": "easy",
                "tags": ["retrieval"],
            }
        ]
    )
    generator = LLMQuestionGenerator(client=_FakeLLMClient(response))
    queries = generator.generate(
        [_classified_invoice()], {"Invoice": []}, max_questions_per_document=5
    )
    assert len(queries) == 1
    assert queries[0].query == "What is the invoice number?"


def test_llm_generator_skips_malformed_response_gracefully() -> None:
    generator = LLMQuestionGenerator(client=_FakeLLMClient("not json"))
    queries = generator.generate(
        [_classified_invoice()], {"Invoice": []}, max_questions_per_document=5
    )
    assert queries == []


def test_llm_generator_only_considers_document_types_in_template_map() -> None:
    generator = LLMQuestionGenerator(client=_FakeLLMClient("[]"))
    queries = generator.generate([_classified_invoice()], {}, max_questions_per_document=5)
    assert queries == []
