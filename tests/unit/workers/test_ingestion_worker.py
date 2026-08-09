from tests.conftest import (
    make_parsed_document,

    FakeSessionFactory,
    FakeAsyncSession,
)
from tests.factories import make_chunk
from tests.factories import make_document
import app.rag.chunker as chunker_module
import app.rag.embeddings as embeddings_module
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import pytest
import app.workers.ingestion_worker as worker


class FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_ingest_document_calls_async_pipeline(monkeypatch):
    document_id = "00000000-0000-0000-0000-000000000004"

    expected = {
        "document_id": document_id,
        "status": "indexed",
        "chunks": 2,
        "pages": 1,
        "latency_s": 0.01,
    }

    called = {}

    async def fake_async(**kwargs):
        called.update(kwargs)
        return expected

    monkeypatch.setattr(
        worker,
        "_ingest_document_async",
        fake_async,
    )

    result = worker.ingest_document(
        document_id,
        "/tmp/invoice.pdf",
        "application/pdf",
        "invoice.pdf",
        500,
        50,
    )


    assert result == expected

    assert called["task"].name == worker.ingest_document.name
    assert called["document_id"] == document_id
    assert called["file_path"] == "/tmp/invoice.pdf"
    assert called["mime_type"] == "application/pdf"
    assert called["document_name"] == "invoice.pdf"
    assert called["chunk_size"] == 500
    assert called["chunk_overlap"] == 50
    assert called["original_filename"] is None


def test_ingest_document_exception(monkeypatch):
    async def fake_async(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        worker,
        "_ingest_document_async",
        fake_async,
    )

    with pytest.raises(RuntimeError, match="boom"):
        worker.ingest_document(
            MagicMock(),
            "123",
            "/tmp/test.pdf",
            "application/pdf",
            "test.pdf",
        )

@pytest.mark.asyncio
async def test_ingest_document_calls_async(monkeypatch):
    called = {}

    async def fake_async(**kwargs):
        called.update(kwargs)
        return {"status": "indexed"}

    monkeypatch.setattr(
        worker,
        "_ingest_document_async",
        fake_async,
    )

    task = MagicMock()
    task.name = "test-task"

    result = await worker._ingest_document_async(
        task=task,
        document_id="123",
        file_path="/tmp/test.pdf",
        mime_type="application/pdf",
        document_name="test.pdf",
        chunk_size=None,
        chunk_overlap=None,
        original_filename=None,
    )

    assert result["status"] == "indexed"

    assert called["task"] is task
    assert called["document_id"] == "123"
    assert called["file_path"] == "/tmp/test.pdf"
    assert called["mime_type"] == "application/pdf"
    assert called["document_name"] == "test.pdf"
    assert called["chunk_size"] is None
    assert called["chunk_overlap"] is None
    assert called["original_filename"] is None


@pytest.mark.asyncio
async def test_ingest_document_async_success(monkeypatch):
    document_id = "00000000-0000-0000-0000-000000000001"

    parsed_doc = SimpleNamespace(
        total_pages=2,
    )

    chunks = [
        make_chunk(
            content="chunk 1",
            page_number=1,
            chunk_index=0,
        ),
        make_chunk(
            content="chunk 2",
            page_number=2,
            chunk_index=1,
        ),
    ]

    parser = MagicMock()
    parser.parse.return_value = parsed_doc

    chunker = MagicMock()
    chunker.chunk.return_value = chunks

    embedding_service = MagicMock()
    embedding_service.embed_batch = AsyncMock(
        return_value=[
            [0.1, 0.2],
            [0.3, 0.4],
        ]
    )

    vector_store = MagicMock()
    vector_store.ensure_collection = AsyncMock()
    vector_store.upsert_chunks = AsyncMock(
        return_value=["point-1", "point-2"]
    )

    qdrant_client = MagicMock()
    qdrant_client.close = AsyncMock()

    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None

    db = MagicMock()
    db.execute = AsyncMock(return_value=db_result)
    db.commit = AsyncMock()
    db.bind = MagicMock()
    db.__aenter__.return_value = db
    db.__aexit__.return_value = False
    session_factory = FakeSessionFactory(db)

    monkeypatch.setattr(
        "app.rag.chunker.DocumentParser",
        lambda: parser,
    )
    monkeypatch.setattr(
        "app.rag.chunker.DocumentChunker",
        lambda chunk_size=None, chunk_overlap=None: chunker,
    )
    monkeypatch.setattr(
        "app.rag.embeddings.EmbeddingService",
        lambda: embedding_service,
    )
    monkeypatch.setattr(
        "app.rag.retriever.vector_store.VectorStore",
        lambda client: vector_store,
    )
    monkeypatch.setattr(
        "qdrant_client.AsyncQdrantClient",
        lambda **kwargs: qdrant_client,
    )
    monkeypatch.setattr(
        "app.db.session.get_sessionmaker",
        lambda: session_factory,
    )

    result = await worker._ingest_document_async(
        task=MagicMock(),
        document_id=document_id,
        file_path="/tmp/invoice.pdf",
        mime_type="application/pdf",
        document_name="invoice.pdf",
        chunk_size=None,
        chunk_overlap=None,
        original_filename="invoice.pdf",
    )

    assert result["document_id"] == document_id
    assert result["status"] == "indexed"
    assert result["chunks"] == 2
    assert result["pages"] == 2

    parser.parse.assert_called_once_with(
        "/tmp/invoice.pdf",
        "application/pdf",
    )

    chunker.chunk.assert_called_once_with(
        parsed_doc,
        document_id,
    )

    embedding_service.embed_batch.assert_awaited_once_with(
        ["chunk 1", "chunk 2"],
    )

    vector_store.ensure_collection.assert_awaited_once()

    vector_store.upsert_chunks.assert_awaited_once_with(
        chunks=chunks,
        embeddings=[
            [0.1, 0.2],
            [0.3, 0.4],
        ],
        document_id=document_id,
        document_name="invoice.pdf",
        original_filename="invoice.pdf",
    )

    qdrant_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_document_async_fails_when_no_chunks(monkeypatch):
    document_id = "00000000-0000-0000-0000-000000000002"

    parsed_doc = SimpleNamespace(
        total_pages=1,
    )

    parser = MagicMock()
    parser.parse.return_value = parsed_doc

    chunker = MagicMock()
    chunker.chunk.return_value = []

    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None

    db = MagicMock()
    db.execute = AsyncMock(return_value=db_result)
    db.commit = AsyncMock()
    db.bind = MagicMock()
    db.__aenter__.return_value = db
    db.__aexit__.return_value = False
    session_factory = FakeSessionFactory(db)

    task = MagicMock()
    task.request.retries = 0
    task.retry.side_effect = RuntimeError("retry")

    monkeypatch.setattr(
        "app.rag.chunker.DocumentParser",
        lambda: parser,
    )
    monkeypatch.setattr(
        "app.rag.chunker.DocumentChunker",
        lambda chunk_size=None, chunk_overlap=None: chunker,
    )
    monkeypatch.setattr(
        "app.db.session.get_sessionmaker",
        lambda: session_factory,
    )

    with pytest.raises(RuntimeError, match="retry"):
        await worker._ingest_document_async(
            task=task,
            document_id=document_id,
            file_path="/tmp/empty.pdf",
            mime_type="application/pdf",
            document_name="empty.pdf",
            chunk_size=None,
            chunk_overlap=None,
            original_filename=None,
        )

    parser.parse.assert_called_once()
    chunker.chunk.assert_called_once()

    task.retry.assert_called_once()

    retry_kwargs = task.retry.call_args.kwargs

    assert retry_kwargs["countdown"] == 30


@pytest.mark.asyncio
async def test_ingest_document_async_retries_on_pipeline_error(monkeypatch):
    document_id = "00000000-0000-0000-0000-000000000003"

    parser = MagicMock()
    parser.parse.side_effect = RuntimeError("parser failed")

    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None

    db = MagicMock()
    db.execute = AsyncMock(return_value=db_result)
    db.commit = AsyncMock()
    db.bind = MagicMock()
    db.__aenter__.return_value = db
    db.__aexit__.return_value = False
    session_factory = FakeSessionFactory(db)

    task = MagicMock()
    task.request.retries = 1
    task.retry.side_effect = RuntimeError("retry")

    monkeypatch.setattr(
        "app.rag.chunker.DocumentParser",
        lambda: parser,
    )
    monkeypatch.setattr(
        "app.db.session.get_sessionmaker",
        lambda: session_factory,
    )

    with pytest.raises(RuntimeError, match="retry"):
        await worker._ingest_document_async(
            task=task,
            document_id=document_id,
            file_path="/tmp/broken.pdf",
            mime_type="application/pdf",
            document_name="broken.pdf",
            chunk_size=None,
            chunk_overlap=None,
            original_filename=None,
        )

    task.retry.assert_called_once()

    retry_kwargs = task.retry.call_args.kwargs

    assert retry_kwargs["exc"].args == ("parser failed",)
    assert retry_kwargs["countdown"] == 60




@pytest.mark.asyncio
async def test_ingest_document_embedding_failure(monkeypatch):
    parser = MagicMock()
    parser.parse.return_value = make_parsed_document()

    chunker = MagicMock()
    chunker.chunk.return_value = [make_chunk()]

    embedding = AsyncMock()
    embedding.embed_batch.side_effect = RuntimeError("boom")

    monkeypatch.setattr(chunker_module, "DocumentParser", lambda: parser)
    monkeypatch.setattr(chunker_module, "DocumentChunker", lambda **_: chunker)
    monkeypatch.setattr(embeddings_module, "EmbeddingService", lambda: embedding)

    document = make_document()

    session = FakeAsyncSession(document)

    monkeypatch.setattr(
        "app.db.session.get_sessionmaker",
        lambda: FakeSessionFactory(session),
    )

    task = MagicMock()
    task.request.retries = 0
    task.retry.side_effect = RuntimeError("retry")

    with pytest.raises(RuntimeError, match="retry"):
        await worker._ingest_document_async(
            task=task,
            document_id=str(document.id),
            file_path="/tmp/test.pdf",
            mime_type="application/pdf",
            document_name="test.pdf",
            chunk_size=None,
            chunk_overlap=None,
            original_filename=None,
        )

    assert document.status == "failed"
    task.retry.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_document_no_chunks(monkeypatch):
    parser = MagicMock()
    parser.parse.return_value = make_parsed_document()

    chunker = MagicMock()
    chunker.chunk.return_value = []

    monkeypatch.setattr(chunker_module, "DocumentParser", lambda: parser)
    monkeypatch.setattr(chunker_module, "DocumentChunker", lambda **_: chunker)

    document = make_document()

    session = FakeAsyncSession(document)

    monkeypatch.setattr(
        "app.db.session.get_sessionmaker",
        lambda: FakeSessionFactory(session),
    )

    task = MagicMock()
    task.request.retries = 0
    task.retry.side_effect = RuntimeError("retry")

    with pytest.raises(RuntimeError, match="retry"):
        await worker._ingest_document_async(
            task=task,
            document_id=str(document.id),
            file_path="/tmp/test.pdf",
            mime_type="application/pdf",
            document_name="test.pdf",
            chunk_size=None,
            chunk_overlap=None,
            original_filename=None,
        )

    assert document.status == "failed"
    task.retry.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_document_success(monkeypatch):
    session = AsyncMock()

    session.__aenter__.return_value = session
    session.__aexit__.return_value = None

    session.begin.return_value = session

    # AsyncSession.add() is synchronous.
    session.add = MagicMock()

    document = make_document()

    result = MagicMock()
    result.scalar_one_or_none.return_value = document
    session.execute.return_value = result





