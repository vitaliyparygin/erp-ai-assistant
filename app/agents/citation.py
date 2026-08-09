from app.agents.state import AgentState
from app.core.logging import get_logger
from app.models.schemas import Citation
from app.llm.protocol import LLMProtocol
from app.rag.prompts import CITATION_EXTRACTION_TEMPLATE
from uuid import UUID

logger = get_logger(__name__)


class CitationAgent:
    """
    Extracts citations from the answer and maps them to source chunks.
    """

    def __init__(self, llm: LLMProtocol) -> None:
        self._llm = llm

    def _build_chain(self):
        return CITATION_EXTRACTION_TEMPLATE | self._llm

    async def __call__(self, state: AgentState):

        if not state.final_answer or not state.reranked_chunks:
            return {
                "citations": [],
                "execution_path": ["citation"],
            }
        return {
            "citations": [
                Citation(
                    document_id=UUID(c.document_id),
                    document_name=c.document_name,
                    page_number=c.page_number,
                    chunk_content=c.content[:300],
                    relevance_score=c.score,
                    chunk_index=c.chunk_index,
                )
                for c in state.reranked_chunks[:3]
            ]
        }
