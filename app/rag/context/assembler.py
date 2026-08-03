from app.config.constants import MAX_CONTEXT
from app.models.schemas import RetrievedChunk

class ContextAssembler:
    def __init__(self, max_context: int = MAX_CONTEXT) -> None:
        self._max_context = max_context

    def build(
        self,
        chunks: list[RetrievedChunk],
        *,
        limit: int = 2,
    ) -> str:
        """Format chunks into a readable context string."""
        if not chunks:
            return ""

        parts = []
        for i, chunk in enumerate(chunks, 1):
            page_info = f" (page {chunk.page_number})" if chunk.page_number else ""
            parts.append(
                f"[Source {i}: {chunk.document_name}{page_info}, score={chunk.score:.3f}]\n"
                f"{chunk.content}"
            )
        context = "\n\n---\n\n".join(parts)
        return context[:MAX_CONTEXT]