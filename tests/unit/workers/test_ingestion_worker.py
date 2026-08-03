import pytest
from app.workers.ingestion_worker import ingest_document
from unittest.mock import MagicMock
from tests.conftest import (
    make_parsed_document,
    make_chunk,
    FakeSessionFactory,
    FakeAsyncSession,
)
from unittest.mock import AsyncMock
from tests.factories import make_document
import app.rag.chunker as chunker_module
import app.rag.embeddings as embeddings_module
from app.workers.ingestion_worker import _ingest_document_async


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
        await _ingest_document_async(
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
        await _ingest_document_async(
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


def test_ingest_document_exception(monkeypatch):
    monkeypatch.setattr(
        "app.workers.ingestion_worker._ingest_document_async",
        lambda **kwargs: None,
    )

    def fake_run(_):
        raise RuntimeError("boom")

    monkeypatch.setattr("asyncio.run", fake_run)

    with pytest.raises(RuntimeError):
        ingest_document.run(
            document_id="1",
            file_path="a",
            mime_type="application/pdf",
            document_name="a",
        )


def test_ingest_document_calls_async(monkeypatch):
    called = {}

    async def fake_async(**kwargs):
        called.update(kwargs)
        return {"status": "indexed"}

    monkeypatch.setattr(
        "app.workers.ingestion_worker._ingest_document_async",
        fake_async,
    )

    result = ingest_document.run(
        document_id="123",
        file_path="/tmp/test.pdf",
        mime_type="application/pdf",
        document_name="test.pdf",
    )

    assert result["status"] == "indexed"

    assert called["task"].name == ingest_document.name
    assert called["document_id"] == "123"
    assert called["file_path"] == "/tmp/test.pdf"
    assert called["mime_type"] == "application/pdf"
    assert called["document_name"] == "test.pdf"
    assert called["chunk_size"] is None
    assert called["chunk_overlap"] is None
    assert called["original_filename"] is None
