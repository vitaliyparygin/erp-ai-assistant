import logging

from langchain_ollama import ChatOllama

from app.config.constants import PROTECTED_TERMS, REWRITE_MAP
from app.rag.prompts import QUERY_REWRITE_TEMPLATE
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class QueryRewriter:
    """Rewrites user queries for improved semantic retrieval."""

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def rewrite(self, state: AgentState) -> str:
        query = state.query.strip()

        if not query:
            return query

        if self._is_protected(query):
            logger.debug(
                "query_rewrite_skipped",
                extra={"query": query},
            )
            return query

        query = self._apply_deterministic_expansions(query)

        if not self._llm:
            return query

        return await self._llm_rewrite(
            query=query,
            state=state,
        )

    @staticmethod
    def _is_protected(query: str) -> bool:
        query_lower = query.lower()

        return any(
            term.lower() in query_lower
            for term in PROTECTED_TERMS
        )

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
    ) -> str:
        context = self._build_context(state)

        chain = QUERY_REWRITE_TEMPLATE | self._llm

        result = await chain.ainvoke(
            {
                "query": query,
                "conversation_context": context,
            }
        )

        content = result.content

        if not isinstance(content, str):
            raise TypeError(
                "Expected string response, "
                f"got {type(content).__name__}"
            )

        rewritten = content.strip()

        return rewritten or query

    @staticmethod
    def _build_context(state: AgentState) -> str:
        if not state.messages:
            return "No prior context"

        return "\n".join(
            f"{message.type}: {message.content[:200]}"
            for message in state.messages[-4:]
        )[:3000]