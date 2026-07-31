from tests.conftest import make_chunk
import pytest
from app.models.schemas import RetrievedChunk
from app.rag.retriever import Reranker, VectorRetriever
from unittest.mock import AsyncMock
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_rerank_top_k_larger_than_docs():
    reranker = Reranker()

    chunk = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="invoice.pdf",
        content="invoice",
        page_number=1,
        score=0.8,
        chunk_index=0,
        metadata={},
    )

    result = await reranker.rerank(
        "invoice",
        [chunk],
        top_k=10,
    )

    assert len(result) == 1


@pytest.mark.asyncio
async def test_rerank_orders_documents():
    reranker = Reranker()

    low = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="invoice.pdf",
        content="random",
        page_number=1,
        score=0.2,
        chunk_index=0,
        metadata={},
    )

    high = RetrievedChunk(
        chunk_id="2",
        document_id="2",
        document_name="contract.pdf",
        content="Contract number: 123",
        page_number=1,
        score=0.1,
        chunk_index=0,
        metadata={},
    )

    result = await reranker.rerank(
        "contract",
        [low, high],
    )

    assert result[0].document_name == "contract.pdf"


def test_get_filter_condition_none():
    retriever = VectorRetriever(
        AsyncMock(),
        AsyncMock(),
    )

    assert retriever.get_filter_condition() is None


@pytest.mark.asyncio
async def test_get_contract_documents():
    client = AsyncMock()

    client.scroll.return_value = (
        [
            MagicMock(
                payload={
                    "document_type": "contract",
                    "document_name": "c1.pdf",
                    "contract_number": "1",
                    "valid_until": "2030",
                }
            ),
            MagicMock(
                payload={
                    "document_type": "invoice",
                    "document_name": "i1.pdf",
                }
            ),
        ],
        None,
    )

    retriever = VectorRetriever(
        client,
        AsyncMock(),
    )

    result = await retriever.get_contract_documents()

    assert len(result) == 1
    assert result[0]["document_name"] == "c1.pdf"


@pytest.mark.asyncio
async def test_rerank_invoice_penalty():
    reranker = Reranker()

    invoice = make_chunk(
        content="""
        invoice
        contractor:
        customer:
        """,
        score=0.5,
    )

    contract = make_chunk(
        content="""
        service agreement
        contract number
        contractor:
        customer:
        """,
        score=0.5,
        chunk_index=1,
    )

    result = await reranker.rerank(
        "contract",
        [invoice, contract],
    )

    assert result[0].chunk_id == contract.chunk_id


@pytest.mark.asyncio
async def test_rerank_important_term(monkeypatch):
    from app.rag import retriever as retriever_module

    monkeypatch.setattr(
        retriever_module,
        "IMPORTANT_TERMS",
        {"critical"},
    )

    reranker = Reranker()

    important = make_chunk(
        content="critical value",
        score=0.3,
    )

    other = make_chunk(
        content="value",
        score=0.3,
        chunk_index=1,
    )

    result = await reranker.rerank(
        "critical",
        [other, important],
    )

    assert result[0].chunk_id == important.chunk_id


@pytest.mark.asyncio
async def test_rerank_term_expansion(monkeypatch):
    from app.rag import retriever as retriever_module

    monkeypatch.setattr(
        retriever_module,
        "TERM_EXPANSIONS",
        {
            "agreement": {"contract"},
        },
    )

    reranker = Reranker()

    contract = make_chunk(
        content="contract number 123",
        score=0.3,
    )

    other = make_chunk(
        content="nothing",
        score=0.3,
        chunk_index=1,
    )

    result = await reranker.rerank(
        "agreement",
        [other, contract],
    )

    assert result[0].chunk_id == contract.chunk_id


@pytest.mark.asyncio
async def test_rerank_document_hint_boost(monkeypatch):
    from app.rag import retriever as retriever_module

    monkeypatch.setattr(
        retriever_module,
        "DOCUMENT_HINTS",
        {
            "invoice": {
                "invoice.pdf": 2.0,
            }
        },
    )

    reranker = Reranker()

    invoice = make_chunk(
        content="random",
        document_name="invoice.pdf",
        score=0.4,
    )

    other = make_chunk(
        content="random",
        document_name="other.pdf",
        score=0.4,
        chunk_index=1,
    )

    result = await reranker.rerank(
        "invoice",
        [other, invoice],
    )

    assert result[0].document_name == "invoice.pdf"


@pytest.mark.asyncio
async def test_rerank_preserves_order_without_boost():
    reranker = Reranker()

    high = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="a.pdf",
        content="abc",
        page_number=1,
        chunk_index=0,
        score=0.95,
        metadata={},
    )

    low = RetrievedChunk(
        chunk_id="2",
        document_id="2",
        document_name="b.pdf",
        content="xyz",
        page_number=1,
        chunk_index=1,
        score=0.5,
        metadata={},
    )

    result = await reranker.rerank(
        "something",
        [low, high],
    )

    assert result[0].chunk_id == "1"


@pytest.mark.asyncio
async def test_rerank_contractor_boost():
    reranker = Reranker()

    contractor = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="contract",
        content="Contractor: ACME Ltd",
        page_number=1,
        score=0.4,
        chunk_index=0,
        metadata={},
    )

    other = RetrievedChunk(
        chunk_id="2",
        document_id="2",
        document_name="invoice",
        content="invoice",
        page_number=1,
        score=0.6,
        chunk_index=0,
        metadata={},
    )

    result = await reranker.rerank(
        "contractor",
        [other, contractor],
    )

    assert result[0].document_name == "contract"


@pytest.mark.asyncio
async def test_rerank_eic_boost():
    reranker = Reranker()

    eic = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="contract",
        content="EIC: 123456789",
        page_number=1,
        score=0.4,
        chunk_index=0,
        metadata={},
    )

    other = RetrievedChunk(
        chunk_id="2",
        document_id="2",
        document_name="invoice",
        content="invoice",
        page_number=1,
        score=0.6,
        chunk_index=0,
        metadata={},
    )

    result = await reranker.rerank(
        "eic",
        [other, eic],
    )

    assert result[0].document_name == "contract"


@pytest.mark.asyncio
async def test_rerank_stage_boost():
    reranker = Reranker()

    stage = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="project",
        content="Stage: Development",
        page_number=1,
        score=0.5,
        chunk_index=0,
        metadata={},
    )

    other = RetrievedChunk(
        chunk_id="2",
        document_id="2",
        document_name="other",
        content="nothing",
        page_number=1,
        score=0.7,
        chunk_index=0,
        metadata={},
    )

    result = await reranker.rerank(
        "stage",
        [other, stage],
    )

    assert result[0].document_name == "project"


@pytest.mark.asyncio
async def test_rerank_customer_boost():
    reranker = Reranker()

    a = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="a",
        content="Customer: OpenAI",
        page_number=1,
        score=0.5,
        chunk_index=0,
        metadata={},
    )

    b = RetrievedChunk(
        chunk_id="2",
        document_id="2",
        document_name="b",
        content="random text",
        page_number=1,
        score=0.7,
        chunk_index=0,
        metadata={},
    )

    result = await reranker.rerank(
        "customer",
        [b, a],
    )

    assert result[0].document_name == "a"


@pytest.mark.asyncio
async def test_rerank_contract_boost():
    reranker = Reranker()

    contract = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="contract.pdf",
        content="""
        Service Agreement
        Contract Number: 42
        Contractor: ABC
        Customer: XYZ
        """,
        page_number=1,
        score=0.6,
        chunk_index=0,
        metadata={},
    )

    invoice = RetrievedChunk(
        chunk_id="2",
        document_id="2",
        document_name="invoice.pdf",
        content="Invoice total amount",
        page_number=1,
        score=0.7,
        chunk_index=0,
        metadata={},
    )

    result = await reranker.rerank(
        "contract",
        [invoice, contract],
    )

    assert result[0].document_name == "contract.pdf"


@pytest.mark.asyncio
async def test_rerank_top_k():
    reranker = Reranker()

    chunks = [
        RetrievedChunk(
            chunk_id=str(i),
            document_id="d",
            document_name=f"doc{i}",
            content="contract customer",
            page_number=1,
            score=float(i),
            chunk_index=i,
            metadata={},
        )
        for i in range(5)
    ]

    result = await reranker.rerank(
        "contract",
        chunks,
        top_k=2,
    )

    assert len(result) == 2


@pytest.mark.asyncio
async def test_rerank_empty():
    reranker = Reranker()

    result = await reranker.rerank(
        query="contract",
        chunks=[],
    )

    assert result == []
