from app.agents.retriever import RetrieverAgent
from app.models.schemas import RetrievedChunk


def test_context_format_matches_golden():
    chunks = [
        RetrievedChunk(
            chunk_id="1",
            document_id="1",
            document_name="Invoice.pdf",
            page_number=3,
            chunk_index=0,
            score=0.92,
            content="Invoice text",
        )
    ]

    context = RetrieverAgent._format_context(chunks)

    assert context == ("[Source 1: Invoice.pdf (page 3), score=0.920]\nInvoice text")
