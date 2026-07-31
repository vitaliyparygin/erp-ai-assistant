from app.agents.retriever import get_unique_docs
from app.models.schemas import RetrievedChunk


def chunk(name: str, page: int):
    return RetrievedChunk(
        chunk_id=f"{name}-{page}",
        document_id=f"00000000-0000-0000-0000-{page:012}",
        document_name=name,
        content="text",
        page_number=page,
        score=0.9,
        chunk_index=page,
        metadata={},
    )


def test_duplicate_documents_removed():
    docs = [
        chunk("Invoice.pdf", 1),
        chunk("Invoice.pdf", 2),
        chunk("Invoice.pdf", 3),
    ]

    unique = get_unique_docs(docs)

    assert len(unique) == 1
    assert "Invoice.pdf" in unique


def test_multiple_documents_preserved():
    docs = [
        chunk("Invoice.pdf", 1),
        chunk("Contract.pdf", 1),
        chunk("Invoice.pdf", 2),
    ]

    unique = get_unique_docs(docs)

    assert len(unique) == 2
