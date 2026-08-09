from app.config.constants import MAX_CONTEXT_ANALYSIS
from app.models.schemas import RetrievedChunk


class ContextAssembler:
    def __init__(self, max_context: int = MAX_CONTEXT_ANALYSIS) -> None:
        self._max_context = max_context

    def build(
        self,
        chunks: list[RetrievedChunk],
    ) -> str:
        if not chunks:
            return ""

        parts = []

        for i, chunk in enumerate(chunks, 1):
            page_info = f" (page {chunk.page_number})" if chunk.page_number else ""

            parts.append(
                f"[Source {i}: {chunk.document_name}{page_info}, "
                f"score={chunk.score:.3f}]\n"
                f"{chunk.content}"
            )

        context = "\n\n---\n\n".join(parts)

        return context[: self._max_context]
