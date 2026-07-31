from app.rag.retriever import VectorStore
from qdrant_client.models import MatchAny
from qdrant_client.models import MatchValue
from types import SimpleNamespace
from app.core.exceptions import VectorStoreError
from app.rag.chunker import TextChunk
from tests.conftest import make_chunk
from app.core.exceptions import RetrievalError
from app.rag.embeddings import EmbeddingService
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.rag.retriever import VectorRetriever
from app.models.schemas import RetrievedChunk
from app.rag.retriever import Reranker


@pytest.mark.asyncio
async def test_rerank_keeps_score_order():
    reranker = Reranker()

    high = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="a.pdf",
        content="nothing",
        score=0.91,
        chunk_index=0,
        metadata={},
    )

    low = RetrievedChunk(
        chunk_id="2",
        document_id="1",
        document_name="a.pdf",
        content="nothing",
        score=0.55,
        chunk_index=1,
        metadata={},
    )

    result = await reranker.rerank(
        "xyz",
        [low, high],
    )

    assert result[0].chunk_id == "1"


@pytest.mark.asyncio
async def test_rerank_similarity_bonus():
    reranker = Reranker()

    chunk1 = RetrievedChunk(
        chunk_id="1",
        document_id="1",
        document_name="a.pdf",
        content="invoice customer payment total amount",
        score=0.5,
        chunk_index=0,
        metadata={},
    )

    chunk2 = RetrievedChunk(
        chunk_id="2",
        document_id="1",
        document_name="a.pdf",
        content="hello world",
        score=0.5,
        chunk_index=1,
        metadata={},
    )

    result = await reranker.rerank(
        "invoice customer",
        [chunk2, chunk1],
    )

    assert result[0].chunk_id == "1"


@pytest.mark.asyncio
async def test_retrieve_custom_score_threshold():
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response
    client.count.return_value = 0

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    await retriever.retrieve(
        "invoice",
        score_threshold=0.87,
    )

    kwargs = client.query_points.await_args.kwargs

    assert kwargs["score_threshold"] == 0.87


@pytest.mark.asyncio
async def test_retrieve_custom_top_k():
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response
    client.count.return_value = 0

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    await retriever.retrieve(
        "invoice",
        top_k=7,
    )

    kwargs = client.query_points.await_args.kwargs

    assert kwargs["limit"] == 7


@pytest.mark.asyncio
async def test_retrieve_with_query_metadata_filter():
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response
    client.count.return_value = 0

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    await retriever.retrieve(
        "invoice",
        query_metadata={
            "customer_name": "ACME",
            "intent": "search",
        },
    )

    kwargs = client.query_points.await_args.kwargs

    assert kwargs["query_filter"] is not None


@pytest.mark.asyncio
async def test_retrieve_with_document_ids_filter():
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response
    client.count.return_value = 0

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    await retriever.retrieve(
        "invoice",
        document_ids=["doc-1"],
    )

    kwargs = client.query_points.await_args.kwargs

    assert kwargs["query_filter"] is not None


@pytest.mark.asyncio
async def test_retrieve_payload_none():
    client = AsyncMock()

    point = MagicMock()
    point.payload = None
    point.score = 0.8
    point.id = "1"

    response = MagicMock()
    response.points = [point]

    client.query_points.return_value = response

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    result = await retriever.retrieve("invoice")

    assert result == []


@pytest.mark.asyncio
async def test_retrieve_debug_query():
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    result = await retriever.retrieve("debug: invoice")

    assert result == []


@pytest.mark.asyncio
async def test_retrieve_custom_threshold():
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    await retriever.retrieve(
        "invoice",
        score_threshold=0.42,
    )

    _, kwargs = client.query_points.await_args

    assert kwargs["score_threshold"] == 0.42


@pytest.mark.asyncio
async def test_retrieve_with_query_metadata(monkeypatch):
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    filter_obj = object()

    called = {}

    def fake_filter(metadata, docs):
        called["metadata"] = metadata
        called["docs"] = docs
        return filter_obj

    monkeypatch.setattr(
        retriever,
        "get_filter_condition",
        fake_filter,
    )

    await retriever.retrieve(
        "invoice",
        query_metadata={"customer": "Acme"},
    )

    assert called["metadata"] == {"customer": "Acme"}
    assert called["docs"] is None

    _, kwargs = client.query_points.await_args
    assert kwargs["query_filter"] is filter_obj


@pytest.mark.asyncio
async def test_retrieve_uses_default_top_k():
    client = AsyncMock()

    response = MagicMock()
    response.points = []

    client.query_points.return_value = response

    embedder = AsyncMock(spec=EmbeddingService)
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    await retriever.retrieve("hello")

    _, kwargs = client.query_points.await_args

    assert kwargs["limit"] == retriever._settings.rag_top_k


@pytest.mark.asyncio
async def test_retrieve_passes_filter(monkeypatch):
    client = AsyncMock()

    response = MagicMock()
    response.points = []

    client.query_points.return_value = response

    embedder = AsyncMock(spec=EmbeddingService)
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    fake_filter = object()

    monkeypatch.setattr(
        retriever,
        "get_filter_condition",
        lambda metadata, docs: fake_filter,
    )

    await retriever.retrieve(
        "invoice",
        document_ids=["doc1"],
    )

    _, kwargs = client.query_points.await_args

    assert kwargs["query_filter"] is fake_filter


@pytest.mark.asyncio
async def test_retrieve_qdrant_failure():
    client = AsyncMock()
    client.query_points.side_effect = RuntimeError("boom")

    embedder = AsyncMock(spec=EmbeddingService)
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    with pytest.raises(RetrievalError):
        await retriever.retrieve("invoice")


@pytest.mark.asyncio
async def test_retrieve_empty_result(monkeypatch):
    client = AsyncMock()

    response = MagicMock()
    response.points = []
    client.query_points.return_value = response

    embedder = AsyncMock(spec=EmbeddingService)
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    result = await retriever.retrieve("hello")

    assert result == []
    embedder.embed_text.assert_awaited_once()
    client.query_points.assert_awaited_once()


@pytest.mark.asyncio
async def test_vector_store_delete_document_failure():
    client = AsyncMock()
    client.delete.side_effect = RuntimeError("boom")

    store = VectorStore(client)

    with pytest.raises(VectorStoreError):
        await store.delete_document("doc1")


@pytest.mark.asyncio
async def test_vector_store_delete_document_success():
    client = AsyncMock()

    store = VectorStore(client)

    await store.delete_document("doc1")

    client.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_vector_store_upsert_failure():
    client = AsyncMock()
    client.upsert.side_effect = RuntimeError("boom")

    store = VectorStore(client)

    with pytest.raises(VectorStoreError):
        await store.upsert_chunks(
            chunks=[make_chunk()],
            embeddings=[[0.1, 0.2]],
            document_id="doc1",
            document_name="stored.pdf",
            original_filename="original.pdf",
        )


@pytest.mark.asyncio
async def test_vector_store_upsert_success():
    client = AsyncMock()

    store = VectorStore(client)

    ids = await store.upsert_chunks(
        chunks=[make_chunk()],
        embeddings=[[0.1, 0.2]],
        document_id="doc1",
        document_name="stored.pdf",
        original_filename="original.pdf",
    )

    assert len(ids) == 1

    client.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_vector_store_upsert_count_mismatch():
    client = AsyncMock()

    store = VectorStore(client)

    with pytest.raises(VectorStoreError):
        await store.upsert_chunks(
            chunks=[make_chunk()],
            embeddings=[],
            document_id="doc1",
            document_name="a.pdf",
            original_filename="a.pdf",
        )


@pytest.mark.asyncio
async def test_vector_store_ensure_collection_error():
    client = AsyncMock()
    client.collection_exists.side_effect = RuntimeError("boom")

    store = VectorStore(client)

    with pytest.raises(VectorStoreError):
        await store.ensure_collection()


@pytest.mark.asyncio
async def test_vector_store_ensure_collection_create():
    client = AsyncMock()
    client.collection_exists.return_value = False

    store = VectorStore(client)

    await store.ensure_collection()

    client.create_collection.assert_awaited_once()


@pytest.mark.asyncio
async def test_vector_store_ensure_collection_exists():
    client = AsyncMock()
    client.collection_exists.return_value = True

    store = VectorStore(client)

    await store.ensure_collection()

    client.collection_exists.assert_awaited_once()
    client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_chunks_exception():
    client = AsyncMock()

    client.upsert.side_effect = Exception("boom")

    store = VectorStore(client)

    chunk = TextChunk(
        content="abc",
        chunk_index=0,
        page_number=1,
        metadata={},
    )

    embeddings = [[0.1] * store._vector_size]

    with pytest.raises(VectorStoreError):
        await store.upsert_chunks(
            chunks=[chunk],
            embeddings=embeddings,
            document_id="1",
            document_name="a.pdf",
            original_filename="a.pdf",
        )


@pytest.mark.asyncio
async def test_ensure_collection_error():
    client = AsyncMock()

    client.collection_exists.side_effect = Exception("boom")

    store = VectorStore(client)

    with pytest.raises(VectorStoreError):
        await store.ensure_collection()


@pytest.mark.asyncio
async def test_delete_document_failure():
    client = AsyncMock()
    client.delete.side_effect = RuntimeError("boom")

    store = VectorStore(client)

    with pytest.raises(VectorStoreError):
        await store.delete_document("doc1")


@pytest.mark.asyncio
async def test_delete_document_success():
    client = AsyncMock()

    store = VectorStore(client)

    await store.delete_document("doc1")

    client.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_chunks_qdrant_failure():
    client = AsyncMock()
    client.upsert.side_effect = RuntimeError("boom")

    store = VectorStore(client)

    chunks = [
        TextChunk(
            content="hello",
            chunk_index=0,
        )
    ]

    embeddings = [[0.1, 0.2]]

    with pytest.raises(VectorStoreError):
        await store.upsert_chunks(
            chunks=chunks,
            embeddings=embeddings,
            document_id="doc",
            document_name="a.pdf",
            original_filename="a.pdf",
        )


@pytest.mark.asyncio
async def test_upsert_chunks_mismatch():
    client = AsyncMock()

    store = VectorStore(client)

    chunks = [
        TextChunk(
            content="hello",
            chunk_index=0,
        )
    ]

    with pytest.raises(VectorStoreError):
        await store.upsert_chunks(
            chunks=chunks,
            embeddings=[],
            document_id="doc",
            document_name="a.pdf",
            original_filename="a.pdf",
        )


@pytest.mark.asyncio
async def test_ensure_collection_already_exists():
    client = AsyncMock()
    client.collection_exists.return_value = True

    store = VectorStore(client)

    await store.ensure_collection()

    client.collection_exists.assert_awaited_once()
    client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_get_contract_documents():
    client = AsyncMock()

    contract = MagicMock()
    contract.payload = {
        "document_type": "contract",
        "document_name": "contract.pdf",
        "contract_number": "42",
        "valid_until": "2027",
    }

    invoice = MagicMock()
    invoice.payload = {
        "document_type": "invoice",
        "document_name": "invoice.pdf",
    }

    client.scroll.return_value = (
        [contract, invoice],
        None,
    )

    retriever = make_retriever()
    retriever._client = client

    docs = await retriever.get_contract_documents()

    assert len(docs) == 1

    assert docs[0]["document_name"] == "contract.pdf"
    assert docs[0]["contract_number"] == "42"


@pytest.mark.asyncio
async def test_retrieve_exception():
    client = AsyncMock()
    client.query_points.side_effect = RuntimeError("boom")

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.3] * 768

    retriever = VectorRetriever(client, embedder)

    with pytest.raises(RetrievalError):
        await retriever.retrieve("hello")


@pytest.mark.asyncio
async def test_retrieve_success():
    client = AsyncMock()

    payload = {
        "document_id": "doc1",
        "original_filename": "invoice.pdf",
        "content": "hello world",
        "page_number": 3,
        "chunk_index": 5,
    }

    point = SimpleNamespace(
        id="123",
        score=0.91,
        payload=payload,
    )

    response = MagicMock()
    response.points = [point]

    client.query_points.return_value = response

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.2] * 768

    retriever = VectorRetriever(client, embedder)

    chunks = await retriever.retrieve("invoice")

    assert len(chunks) == 1

    chunk = chunks[0]

    assert chunk.document_id == "doc1"
    assert chunk.document_name == "invoice.pdf"
    assert chunk.page_number == 3
    assert chunk.chunk_index == 5
    assert chunk.score == 0.91
    assert chunk.content == "hello world"


@pytest.mark.asyncio
async def test_empty_retrieve():
    client = AsyncMock()

    response = MagicMock()
    response.points = []

    client.query_points.return_value = response

    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1] * 768

    retriever = VectorRetriever(client, embedder)

    chunks = await retriever.retrieve("hello")

    assert chunks == []

    embedder.embed_text.assert_awaited_once()
    client.query_points.assert_awaited_once()


def test_get_filter_condition_both():
    retriever = make_retriever()

    filt = retriever.get_filter_condition(
        document_ids=["doc1"],
        query_metadata={
            "document_type": "contract",
        },
    )

    assert filt is not None
    assert len(filt.must) == 2


def test_get_filter_condition_metadata():
    retriever = make_retriever()

    filt = retriever.get_filter_condition(
        query_metadata={
            "document_type": "invoice",
            "vendor": "ACME",
            "intent": "ignored",
        }
    )

    assert filt is not None
    assert len(filt.must) == 2

    keys = {c.key for c in filt.must}

    assert keys == {
        "document_type",
        "vendor",
    }

    for cond in filt.must:
        assert isinstance(cond.match, MatchValue)


def test_get_filter_condition_document_ids():
    retriever = make_retriever()

    filt = retriever.get_filter_condition(
        document_ids=["1", "2"],
    )

    assert filt is not None
    assert len(filt.must) == 1

    cond = filt.must[0]

    assert cond.key == "document_id"
    assert isinstance(cond.match, MatchAny)
    assert cond.match.any == ["1", "2"]


def make_retriever():
    return VectorRetriever(
        qdrant_client=AsyncMock(),
        embedding_service=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_delete_document():
    client = AsyncMock()

    store = VectorStore(client)

    await store.delete_document("doc1")

    client.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_chunks_count_mismatch():
    client = AsyncMock()

    store = VectorStore(client)

    chunks = [
        TextChunk(
            content="hello",
            chunk_index=0,
            metadata={},
        )
    ]

    embeddings = []

    with pytest.raises(VectorStoreError):
        await store.upsert_chunks(
            chunks=chunks,
            embeddings=embeddings,
            document_id="doc",
            document_name="file.pdf",
            original_filename=None,
        )


@pytest.mark.asyncio
async def test_upsert_chunks_success():
    client = AsyncMock()

    store = VectorStore(client)

    chunks = [
        TextChunk(
            content="hello",
            chunk_index=0,
            metadata={},
        ),
        TextChunk(
            content="world",
            chunk_index=1,
            metadata={},
        ),
    ]

    embeddings = [
        [0.1] * store._vector_size,
        [0.2] * store._vector_size,
    ]

    ids = await store.upsert_chunks(
        chunks=chunks,
        embeddings=embeddings,
        document_id="doc1",
        document_name="file.pdf",
        original_filename="file.pdf",
    )

    assert len(ids) == 2

    client.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_collection_failure():
    client = AsyncMock()
    client.collection_exists.side_effect = RuntimeError("boom")

    store = VectorStore(client)

    with pytest.raises(VectorStoreError):
        await store.ensure_collection()


@pytest.mark.asyncio
async def test_ensure_collection_create():
    client = AsyncMock()
    client.collection_exists.return_value = False

    store = VectorStore(client)

    await store.ensure_collection()

    client.collection_exists.assert_awaited_once()
    client.create_collection.assert_awaited_once()


@pytest.mark.asyncio
async def test_ensure_collection_exists():
    client = AsyncMock()
    client.collection_exists.return_value = True

    store = VectorStore(client)

    await store.ensure_collection()

    client.collection_exists.assert_awaited_once()
    client.create_collection.assert_not_called()
