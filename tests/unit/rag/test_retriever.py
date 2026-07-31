import pytest
from unittest.mock import AsyncMock, MagicMock
from app.models.schemas import RetrievedChunk
from app.rag.retriever import VectorRetriever
from app.core.exceptions import RetrievalError


@pytest.mark.asyncio
async def test_retrieve_qdrant_exception():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1]

    client = AsyncMock()
    client.query_points.side_effect = RuntimeError("boom")

    retriever = VectorRetriever(
        client,
        embedder,
    )

    with pytest.raises(RetrievalError):
        await retriever.retrieve("hello")


@pytest.mark.asyncio
async def test_retrieve_skips_empty_payload():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1]

    point = MagicMock()
    point.payload = None

    response = MagicMock()
    response.points = [point]

    client = AsyncMock()
    client.query_points.return_value = response
    client.count.return_value = 0

    retriever = VectorRetriever(
        client,
        embedder,
    )

    chunks = await retriever.retrieve("hello")

    assert chunks == []


@pytest.mark.asyncio
async def test_retrieve_returns_chunks():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1]

    point = MagicMock()
    point.id = "1"
    point.score = 0.95
    point.payload = {
        "document_id": "doc1",
        "original_filename": "invoice.pdf",
        "content": "invoice text",
        "page_number": 2,
        "chunk_index": 5,
    }

    response = MagicMock()
    response.points = [point]

    client = AsyncMock()
    client.query_points.return_value = response
    client.count.return_value = 1

    retriever = VectorRetriever(
        client,
        embedder,
    )

    chunks = await retriever.retrieve("invoice")

    assert len(chunks) == 1
    assert chunks[0].document_id == "doc1"
    assert chunks[0].document_name == "invoice.pdf"
    assert chunks[0].content == "invoice text"
    assert chunks[0].page_number == 2


@pytest.mark.asyncio
async def test_retrieve_calls_query_points():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1]

    response = MagicMock()
    response.points = []

    client = AsyncMock()
    client.query_points.return_value = response
    client.count.return_value = 0

    retriever = VectorRetriever(
        client,
        embedder,
    )

    await retriever.retrieve("hello")

    client.query_points.assert_awaited_once()


@pytest.mark.asyncio
async def test_retrieve_calls_embedder():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1]

    response = MagicMock()
    response.points = []

    client = AsyncMock()
    client.query_points.return_value = response
    client.count.return_value = 0

    retriever = VectorRetriever(
        client,
        embedder,
    )

    await retriever.retrieve("hello")

    embedder.embed_text.assert_awaited_once_with("hello")


def test_get_filter_condition_combined():
    retriever = VectorRetriever(
        MagicMock(),
        MagicMock(),
    )

    filt = retriever.get_filter_condition(
        query_metadata={
            "customer": "ACME",
        },
        document_ids=["abc"],
    )

    assert len(filt.must) == 2


def test_get_filter_condition_metadata():
    retriever = VectorRetriever(
        MagicMock(),
        MagicMock(),
    )

    filt = retriever.get_filter_condition(
        query_metadata={
            "vendor": "IBM",
            "intent": "ignored",
        },
    )

    assert len(filt.must) == 1
    assert filt.must[0].key == "vendor"


def test_get_filter_condition_document_ids():
    retriever = VectorRetriever(
        MagicMock(),
        MagicMock(),
    )

    filt = retriever.get_filter_condition(
        document_ids=["1", "2"],
    )

    assert filt is not None
    assert len(filt.must) == 1
    assert filt.must[0].key == "document_id"


def test_vector_retriever_init():
    client = MagicMock()
    embedder = MagicMock()

    retriever = VectorRetriever(
        qdrant_client=client,
        embedding_service=embedder,
    )

    assert retriever._client is client
    assert retriever._embedder is embedder
    assert retriever._collection is not None


@pytest.mark.asyncio
async def test_retrieve_embedding_exception():
    embeddings = AsyncMock()
    embeddings.embed_text.side_effect = RuntimeError()

    retriever = VectorRetriever(
        AsyncMock(),
        embeddings,
    )

    with pytest.raises(RuntimeError):
        await retriever.retrieve("hello")


@pytest.mark.asyncio
async def test_retrieve_calls_embedding(monkeypatch):
    embeddings = AsyncMock()
    embeddings.embed_text.return_value = [0.1, 0.2]

    qdrant = AsyncMock()
    qdrant.search.return_value = []

    retriever = VectorRetriever(
        qdrant,
        embeddings,
    )

    await retriever.retrieve("hello")

    embeddings.embed_text.assert_awaited_once_with("hello")


@pytest.mark.asyncio
async def test_get_contract_documents_deduplicates():
    client = AsyncMock()

    p1 = MagicMock()
    p1.payload = {
        "document_type": "contract",
        "document_name": "contract.pdf",
        "contract_number": "123",
        "valid_until": "2027",
    }

    p2 = MagicMock()
    p2.payload = dict(p1.payload)

    client.scroll.return_value = ([p1, p2], None)

    retriever = VectorRetriever(client, AsyncMock())

    result = await retriever.get_contract_documents()

    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_contract_documents_empty():
    client = AsyncMock()

    point = MagicMock()
    point.payload = {
        "document_type": "invoice",
        "document_name": "invoice.pdf",
    }

    client.scroll.return_value = ([point], None)

    retriever = VectorRetriever(client, AsyncMock())

    result = await retriever.get_contract_documents()

    assert result == []


@pytest.mark.asyncio
async def test_retrieve_combined_filter():
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
        document_ids=["1", "2"],
        query_metadata={"document_type": "invoice"},
    )

    kwargs = client.query_points.await_args.kwargs

    assert kwargs["query_filter"] is not None
    assert len(kwargs["query_filter"].must) == 2


@pytest.mark.asyncio
async def test_retrieve_uses_custom_top_k():
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
        top_k=3,
    )

    kwargs = client.query_points.await_args.kwargs
    assert kwargs["limit"] == 3


@pytest.mark.asyncio
async def test_retrieve_uses_custom_score_threshold():
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
        score_threshold=0.91,
    )

    kwargs = client.query_points.await_args.kwargs
    assert kwargs["score_threshold"] == 0.91


@pytest.mark.asyncio
async def test_get_contract_documents():
    point = MagicMock()
    point.payload = {
        "document_type": "contract",
        "document_name": "a.pdf",
        "contract_number": "123",
        "valid_until": "2028-01-01",
    }

    client = AsyncMock()
    client.scroll.return_value = ([point], None)

    retriever = VectorRetriever(client, AsyncMock())

    result = await retriever.get_contract_documents()

    assert result == [
        {
            "document_name": "a.pdf",
            "contract_number": "123",
            "valid_until": "2028-01-01",
        }
    ]


@pytest.mark.asyncio
async def test_retrieve_qdrant_failure():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1]

    client = AsyncMock()
    client.query_points.side_effect = RuntimeError("boom")

    retriever = VectorRetriever(client, embedder)

    with pytest.raises(RetrievalError):
        await retriever.retrieve("hello")


@pytest.mark.asyncio
async def test_retrieve_empty():
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1]

    response = MagicMock()
    response.points = []

    client = AsyncMock()
    client.query_points.return_value = response
    client.count.return_value = 0

    retriever = VectorRetriever(client, embedder)

    result = await retriever.retrieve("abc")

    assert result == []


@pytest.mark.asyncio
async def test_retrieve_success(monkeypatch):
    embedder = AsyncMock()
    embedder.embed_text.return_value = [0.1, 0.2]

    point = MagicMock()
    point.id = "p1"
    point.score = 0.93
    point.payload = {
        "document_id": "doc1",
        "document_name": "contract.pdf",
        "original_filename": "contract.pdf",
        "content": "hello world",
        "page_number": 1,
        "chunk_index": 0,
    }

    response = MagicMock()
    response.points = [point]

    client = AsyncMock()
    client.query_points.return_value = response
    client.count.return_value = 1

    retriever = VectorRetriever(client, embedder)

    result = await retriever.retrieve("hello")

    assert len(result) == 1
    assert isinstance(result[0], RetrievedChunk)
    assert result[0].document_id == "doc1"

    embedder.embed_text.assert_awaited_once()
    client.query_points.assert_awaited_once()
