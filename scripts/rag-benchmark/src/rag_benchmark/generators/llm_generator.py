"""LLM-backed question generation.

Uses an injected client so the generator itself has no hard dependency on
a specific SDK version and can be unit tested with a fake client.
"""

from __future__ import annotations

import json
from typing import Protocol

from rag_benchmark.generators.base import QuestionGenerator, QuestionTemplateMap
from rag_benchmark.models import BenchmarkQuery, ClassifiedDocument, Difficulty
from rag_benchmark.utils import get_logger, truncate

logger = get_logger("generators.llm")

_SYSTEM_PROMPT = (
    "You generate realistic search queries a user of a retrieval system "
    "would type to find a specific fact in a specific document. Given a "
    "document type, its extracted metadata fields, and a text excerpt, "
    "return a JSON array of objects with keys: query, expected_fields "
    "(list of field names referenced), difficulty (easy|medium|hard), "
    "tags (list of strings). Return ONLY the JSON array, no prose."
)


class LLMClient(Protocol):
    """Minimal interface an LLM client must satisfy for injection.

    Concrete adapters (e.g. wrapping the Anthropic SDK) implement this so
    LLMQuestionGenerator stays decoupled from any particular SDK.
    """

    def complete(self, system: str, user: str) -> str:
        """Send a single-turn completion request and return raw text."""
        ...


class LLMQuestionGenerator(QuestionGenerator):
    """Generates questions by prompting an injected LLM client per document.

    Args:
        client: Any object implementing LLMClient. Required — this
            generator performs no network calls of its own and will raise
            if no client is supplied, keeping the dependency explicit.
        excerpt_chars: How much document text to include in the prompt.
    """

    def __init__(self, client: LLMClient, excerpt_chars: int = 1500) -> None:
        self._client = client
        self._excerpt_chars = excerpt_chars

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
            if doc_type not in template_map:
                # Templates still define which document types are in-scope,
                # even for LLM generation, so ERP/Medical/etc. plugins stay
                # authoritative about coverage.
                continue

            excerpt = truncate(classified.document.text, self._excerpt_chars)
            user_prompt = (
                f"Document type: {doc_type}\n"
                f"Filename: {classified.document.filename}\n"
                f"Extracted fields: {json.dumps(classified.metadata.as_plain_dict())}\n"
                f"Max questions: {max_questions_per_document}\n"
                f"Excerpt:\n{excerpt}"
            )

            try:
                raw = self._client.complete(system=_SYSTEM_PROMPT, user=user_prompt)
                items = json.loads(raw)
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "LLM generation failed for %s: %s", classified.document.filename, exc
                )
                continue

            for item in items[:max_questions_per_document]:
                print(item)
                try:
                    queries.append(
                        BenchmarkQuery(
                            id=next_id,
                            query=item["query"],
                            expected_document=classified.document.filename,
                            expected_fields=item.get("expected_fields", []),
                            document_type=doc_type,
                            difficulty=Difficulty(item.get("difficulty", "easy")),
                            tags=item.get("tags", []),
                            template_id=item.get("key", '')
                        )
                    )
                    next_id += 1
                except (KeyError, ValueError) as exc:
                    logger.warning("Skipping malformed LLM question item: %s", exc)

        logger.info("Generated %d LLM question(s) from %d document(s)", len(queries), len(documents))
        return queries


class AnthropicLLMClient:
    """Concrete LLMClient adapter for the Anthropic Python SDK.

    Kept as an optional adapter so importing this module does not require
    the `anthropic` package unless this class is actually instantiated.
    """

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 1024) -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "The 'anthropic' package is required for AnthropicLLMClient. "
                "Install with `pip install rag-benchmark[llm]`."
            ) from exc
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
