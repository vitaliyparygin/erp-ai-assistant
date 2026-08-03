import re

from app.config.constants import (
    DOCUMENT_HINTS,
    RERANK_STOP_WORDS,
    TERM_EXPANSIONS,
    IMPORTANT_TERMS
)
from app.models.schemas import RetrievedChunk
from app.core.config import get_settings
from app.config.constants import RERANK_FIELD_BOOSTS
from app.core.logging import get_logger
from dataclasses import dataclass

logger = get_logger(__name__)

def _field_boost(
        content: str,
        marker: str,
        boost: float,
) -> float:
    if marker in content:
        return boost

    return 0.0

def _calculate_field_boost(
        query_terms: set[str],
        content: str,
) -> float:
    boost = 0.0

    if "eic" in query_terms:
        boost += _field_boost(
            content,
            "eic",
            RERANK_FIELD_BOOSTS["eic"],
        )

    if "customer" in query_terms:
        boost += _field_boost(
            content,
            "customer:",
            RERANK_FIELD_BOOSTS["customer"],
        )

    if {"contractor", "executor"} & query_terms:
        boost += _field_boost(
            content,
            "contractor:",
            RERANK_FIELD_BOOSTS["contractor"],
        )

    if "stage" in query_terms:
        boost += _field_boost(
            content,
            "stage:",
            RERANK_FIELD_BOOSTS["stage"],
        )

    return boost




@dataclass(frozen=True)
class ChunkScoreBreakdown:
    vector_score: float
    term_match_boost: float = 0.0
    field_boost: float = 0.0
    document_hint_boost: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.vector_score
            + self.term_match_boost
            + self.field_boost
            + self.document_hint_boost
        )

class Reranker:
    """
    Reranks retrieved chunks using deterministic lexical/domain boosts.

    The initial vector similarity score is preserved as the base score.
    Additional boosts are applied for:
    - query term matches;
    - configured term expansions;
    - ERP field markers;
    - important terms;
    - document-specific hints.
    """
    TERM_EXPANSIONS = TERM_EXPANSIONS
    IMPORTANT_TERMS = IMPORTANT_TERMS
    DOCUMENT_HINTS = DOCUMENT_HINTS

    def __init__(self) -> None:
        self._settings = get_settings()


    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        k = top_k or self._settings.rag_rerank_top_k

        if not chunks:
            return []

        query_terms = self._extract_query_terms(query)

        scored_chunks = []

        for chunk in chunks:
            breakdown = self._score_breakdown(
                chunk=chunk,
                query_terms=query_terms,
            )

            logger.debug(
                "reranker_score",
                document=chunk.document_name,
                chunk_index=chunk.chunk_index,
                vector_score=round(breakdown.vector_score, 4),
                term_match_boost=round(
                    breakdown.term_match_boost,
                    4,
                ),
                field_boost=round(
                    breakdown.field_boost,
                    4,
                ),
                document_hint_boost=round(
                    breakdown.document_hint_boost,
                    4,
                ),
                total_score=round(
                    breakdown.total,
                    4,
                ),
            )

            scored_chunks.append(
                (chunk, breakdown.total)
            )

        scored_chunks.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            chunk
            for chunk, _score in scored_chunks[:k]
        ]

    @staticmethod
    def _extract_query_terms(query: str) -> set[str]:
        query_terms = {
            term
            for term in re.findall(r"\w+", query.lower())
            if term not in RERANK_STOP_WORDS
        }

        expanded_terms = set(query_terms)

        for term in query_terms:
            expanded_terms.update(
                Reranker.TERM_EXPANSIONS.get(term, set())
            )

        return expanded_terms

    def _score_chunk(
            self,
            chunk: RetrievedChunk,
            query_terms: set[str],
    ) -> float:
        return self._score_breakdown(
            chunk=chunk,
            query_terms=query_terms,
        ).total

    @staticmethod
    def _calculate_term_match_boost(
            query_terms: set[str],
            content: str,
    ) -> float:
        content_terms = set(
            re.findall(r"\w+", content)
        )

        term_matches = len(query_terms & content_terms)

        return min(
            term_matches / max(len(query_terms), 1),
            0.2,
        )

    @staticmethod
    def _calculate_document_hint_boost(
            expanded_terms: set[str],
            document_name: str,
    ) -> float:
        boost = 0.0

        for term in expanded_terms:
            boosts = Reranker.DOCUMENT_HINTS.get(term, {})

            if document_name in boosts:
                boost += boosts[document_name]

        return boost

    def _score_breakdown(
            self,
            chunk: RetrievedChunk,
            query_terms: set[str],
    ) -> ChunkScoreBreakdown:
        content_lower = chunk.content.lower()

        return ChunkScoreBreakdown(
            vector_score=chunk.score,
            term_match_boost=self._calculate_term_match_boost(
                query_terms,
                content_lower,
            ),
            field_boost=_calculate_field_boost(
                query_terms,
                content_lower,
            ),
            document_hint_boost=self._calculate_document_hint_boost(
                query_terms,
                chunk.document_name,
            ),
        )





