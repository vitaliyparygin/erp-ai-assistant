import logging

from langchain_core.runnables import Runnable

from app.config.constants import (
    PROTECTED_IDENTIFIER_PATTERN,
    PROTECTED_TERMS,
    REWRITE_MAP,
)
from app.rag.prompts import QUERY_REWRITE_TEMPLATE
from app.agents.state import AgentState
from app.rag.context.conversation import build_conversation_context

logger = logging.getLogger(__name__)


class QueryRewriter:
    """Rewrites user queries for improved semantic retrieval."""

    def __init__(self, llm: Runnable | None) -> None:
        self._llm = llm

        self._chain = QUERY_REWRITE_TEMPLATE | llm if llm is not None else None

    async def rewrite(
        self,
        state: AgentState,
    ) -> tuple[str, dict[str, int]]:
        query = state.query.strip()

        empty_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        if not query:
            return query, empty_usage

        if self._is_protected(query):
            logger.debug(
                "query_rewrite_skipped",
                extra={"query": query},
            )
            return query, empty_usage

        query = self._apply_deterministic_expansions(query)

        if self._llm is None:
            return query, empty_usage

        if PROTECTED_IDENTIFIER_PATTERN.search(query):
            logger.debug(
                "query_rewrite_skipped_protected_identifier: query=%s",
                query,
            )
            return query, empty_usage

        return await self._llm_rewrite(
            query=query,
            state=state,
        )

    @staticmethod
    def _is_protected(query: str) -> bool:
        query_lower = query.lower()

        return any(term.lower() in query_lower for term in PROTECTED_TERMS)

    @staticmethod
    def _apply_deterministic_expansions(query: str) -> str:
        result = query.lower()

        for term, synonyms in REWRITE_MAP.items():
            if term.lower() not in result:
                continue

            additions = " ".join(synonyms)

            if additions:
                result = f"{result} {additions}"

        return result.strip()

    async def _llm_rewrite(
        self,
        query: str,
        state: AgentState,
    ) -> tuple[str, dict[str, int]]:
        conversation_context = build_conversation_context(state)
        if self._chain is None:
            raise ValueError("Chain is not initialized.")
        result = await self._chain.ainvoke(
            {
                "query": query,
                "conversation_context": conversation_context,
            }
        )

        content = result.content

        if not isinstance(content, str):
            raise TypeError(
                f"Expected string content from LLM, got {type(content).__name__}"
            )

        content = content.strip()

        usage = getattr(result, "usage_metadata", None) or {}

        if not content:
            return (
                query,
                {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )

        return (
            content,
            {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        )
