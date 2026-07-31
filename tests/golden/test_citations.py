from app.agents.summarize import build_citations
from app.models.schemas import RetrievedChunk
from tests.factories import make_state
from uuid import uuid4
from rules.models import DocumentType


def test_citations_snapshot():
    state = make_state(
        reranked_chunks=[
            RetrievedChunk(
                chunk_id="chunk-1",
                document_id=str(uuid4()),
                document_name="Invoice.pdf",
                page_number=1,
                chunk_index=0,
                content=DocumentType.INVOICE,
                score=0.95,
            )
        ]
    )

    citations = build_citations(state)

    assert len(citations) == 1
    assert citations[0].document_name == "Invoice.pdf"
