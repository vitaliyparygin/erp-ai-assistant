import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from app.main import app
from unittest.mock import MagicMock
from uuid import uuid4
from app.core.dependencies import get_db_session, get_settings
from pathlib import Path
from tests.factories import make_document, make_settings
from app.models.schemas import DocumentStatus
from types import SimpleNamespace
from app.core.dependencies import RateLimitDep


async def override_rate_limit():
    return None


app.dependency_overrides[RateLimitDep] = override_rate_limit


@pytest.mark.asyncio
async def test_delete_document_removes_file(monkeypatch):
    db = AsyncMock()

    doc = make_document()

    result = MagicMock()
    result.scalar_one_or_none.return_value = doc

    db.execute.return_value = result

    removed = False

    def fake_exists(self):
        return True

    def fake_unlink(self, *args, **kwargs):
        nonlocal removed
        removed = True

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "unlink", fake_unlink)

    async def override_db():
        yield db

    async def override_settings():
        return make_settings()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.delete(f"/api/v1/documents/{doc.id}")

    assert response.status_code == 204
    assert removed

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_document_commits(monkeypatch):
    db = AsyncMock()

    doc = make_document()

    result = MagicMock()
    result.scalar_one_or_none.return_value = doc

    db.execute.return_value = result

    monkeypatch.setattr(Path, "exists", lambda self: False)

    async def override_db():
        yield db

    async def override_settings():
        return make_settings()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.delete(f"/api/v1/documents/{doc.id}")

    assert response.status_code == 204

    db.delete.assert_called_once_with(doc)
    db.commit.assert_awaited_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_document_ready():
    db = AsyncMock()

    doc = make_document(status=DocumentStatus.INDEXED)

    result = MagicMock()
    result.scalar_one_or_none.return_value = doc

    db.execute.return_value = result

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/documents/{doc.id}")

    assert response.status_code == 200
    assert response.json()["is_ready"] is True

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_documents_pagination():
    db = AsyncMock()

    doc = make_document()

    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = [doc]

    count_result = MagicMock()
    count_result.scalar.return_value = 25

    db.execute.side_effect = [
        query_result,
        count_result,
    ]

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/documents/",
            params={
                "page": 2,
                "page_size": 5,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["page"] == 2
    assert body["page_size"] == 5
    assert body["total"] == 25

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_documents_empty():
    db = AsyncMock()

    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = []

    count_result = MagicMock()
    count_result.scalar.return_value = 0

    db.execute.side_effect = [
        query_result,
        count_result,
    ]

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/documents/")

    assert response.status_code == 200

    body = response.json()

    assert body["documents"] == []
    assert body["total"] == 0
    assert body["page"] == 1
    assert body["page_size"] == 20

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_document_empty_filename(tmp_path):
    settings = make_settings(upload_dir=str(tmp_path))

    async def override_settings():
        return settings

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "",
                    b"",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 422

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_document_file_too_large(tmp_path):
    settings = make_settings(
        upload_dir=str(tmp_path),
        allowed_extensions=["pdf"],
        max_upload_size_bytes=1,
        max_upload_size_mb=1,
    )

    async def override_settings():
        return settings

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_db_session] = override_db

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "invoice.pdf",
                        b"123456789",
                        "application/pdf",
                    )
                },
            )

        assert response.status_code == 413
        assert response.json()["detail"].startswith("File 0.0MB exceeds limit")

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_document_invalid_extension(tmp_path):
    settings = make_settings(
        upload_dir=str(tmp_path),
        allowed_extensions=["pdf"],
    )

    async def override_settings():
        return settings

    async def override_db():
        yield AsyncMock()

    app.dependency_overrides[get_settings] = override_settings
    app.dependency_overrides[get_db_session] = override_db

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/documents/upload",
                files={
                    "file": (
                        "virus.exe",
                        b"abc",
                        "application/octet-stream",
                    )
                },
            )

        assert response.status_code == 415
        assert response.json()["detail"] == (
            "File type 'exe' not supported. Allowed: ['pdf']"
        )

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_upload_document_success(monkeypatch, tmp_path):
    db = AsyncMock()

    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    task = SimpleNamespace(id="task-123")

    send_task = MagicMock(return_value=task)

    monkeypatch.setattr(
        "app.workers.celery_app.celery_app.send_task",
        send_task,
    )

    settings = make_settings(
        upload_dir=str(tmp_path),
        allowed_extensions=["pdf"],
        max_upload_size_bytes=1024 * 1024,
    )

    async def override_db():
        yield db

    async def override_settings():
        return settings

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "invoice.pdf",
                    b"hello world",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 202

    body = response.json()

    assert body["status"] == "pending"
    assert body["task_id"] == "task-123"

    send_task.assert_called_once()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_documents_filter_status():
    db = MagicMock()

    doc = make_document(
        status=DocumentStatus.PENDING,
        version=1,
    )

    query_result = MagicMock()

    scalars = MagicMock()
    scalars.all.return_value = [doc]

    query_result.scalars.return_value = scalars

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    db.execute = AsyncMock(
        side_effect=[
            query_result,
            count_result,
        ]
    )

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/documents/",
            params={
                "doc_status": "pending",
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert body["documents"][0]["status"] == "pending"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_document_not_found(monkeypatch):
    db = AsyncMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    doc = make_document()

    Path(doc.file_path).write_text("test")

    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    db.execute.return_value = result

    vector_store = AsyncMock()

    monkeypatch.setattr(
        "app.rag.retriever.vector_store.VectorStore",
        MagicMock(return_value=vector_store),
    )

    client = AsyncMock()

    monkeypatch.setattr(
        "qdrant_client.AsyncQdrantClient",
        MagicMock(return_value=client),
    )

    async def override_db():
        yield db

    async def override_settings():
        return make_settings()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client_http:
        response = await client_http.delete(f"/api/v1/documents/{doc.id}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(monkeypatch):
    db = AsyncMock()
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    doc = make_document()

    Path(doc.file_path).write_text("test")

    result = MagicMock()
    result.scalar_one_or_none.return_value = doc

    db.execute.return_value = result

    vector_store = AsyncMock()

    monkeypatch.setattr(
        "app.rag.retriever.vector_store.VectorStore",
        MagicMock(return_value=vector_store),
    )

    client = AsyncMock()

    monkeypatch.setattr(
        "qdrant_client.AsyncQdrantClient",
        MagicMock(return_value=client),
    )

    async def override_db():
        yield db

    async def override_settings():
        return make_settings()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_settings] = override_settings

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client_http:
        response = await client_http.delete(f"/api/v1/documents/{doc.id}")

    assert response.status_code == 204

    db.delete.assert_awaited_once()
    db.commit.assert_awaited()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_document_not_found():
    db = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None

    db.execute.return_value = result

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/documents/{uuid4()}")

    assert response.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_document():
    db = AsyncMock()

    doc = make_document()

    result = MagicMock()
    result.scalar_one_or_none.return_value = doc

    db.execute.return_value = result

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(f"/api/v1/documents/{doc.id}")

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == str(doc.id)

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_documents():
    db = AsyncMock()

    doc = make_document()

    query_result = MagicMock()
    query_result.scalars.return_value.all.return_value = [doc]

    count_result = MagicMock()
    count_result.scalar.return_value = 1

    db.execute.side_effect = [
        query_result,
        count_result,
    ]

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/documents/")

    assert response.status_code == 200

    body = response.json()

    assert body["total"] == 1
    assert len(body["documents"]) == 1

    app.dependency_overrides.clear()
