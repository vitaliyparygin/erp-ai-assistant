import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock
from app.main import app
from unittest.mock import MagicMock
from tests.factories import make_conversation
from uuid import uuid4
from app.core.dependencies import (
    get_db_session,
    get_redis_client,
)
from app.models.orm import ConversationModel
from datetime import datetime, UTC


@pytest.mark.asyncio
async def test_delete_conversation():

    conversation_id = uuid4()

    conv = ConversationModel(
        id=conversation_id,
        session_id="session-1",
        is_active=True,
        message_count=0,
        total_tokens=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    db = MagicMock()
    db.execute = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv

    db.execute.return_value = result
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    redis = AsyncMock()

    async def override_db():
        yield db

    async def override_redis():
        yield redis

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.delete(
            f"/api/v1/conversations/{conversation_id}",
        )

    assert response.status_code == 204

    db.delete.assert_awaited_once_with(conv)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_archive_conversation_not_found():
    db = MagicMock()
    db.execute = AsyncMock()

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
        response = await client.patch(
            f"/api/v1/conversations/{uuid4()}/archive",
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_archive_conversation_success():
    conv = make_conversation(is_active=True)

    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv
    db.execute.return_value = result

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.patch(
            f"/api/v1/conversations/{conv.id}/archive",
        )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(conv)


@pytest.mark.asyncio
async def test_delete_conversation_not_found():
    db = MagicMock()
    db.execute = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    async def override_db():
        yield db

    async def override_redis():
        yield AsyncMock()

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.delete(
            f"/api/v1/conversations/{uuid4()}",
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_conversation_success():
    conv = make_conversation()

    db = MagicMock()
    db.execute = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv
    db.execute.return_value = result

    db.delete = AsyncMock()
    db.commit = AsyncMock()

    redis = AsyncMock()

    async def override_db():
        yield db

    async def override_redis():
        yield redis

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.delete(
            f"/api/v1/conversations/{conv.id}",
        )

    assert response.status_code == 204

    db.delete.assert_awaited_once_with(conv)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_conversation_by_session_not_found():

    db = MagicMock()
    db.execute = AsyncMock()

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
        response = await client.get(
            "/api/v1/conversations/session/unknown",
        )

    assert response.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_conversation_by_session():

    conv = make_conversation(
        session_id="session-123",
    )

    db = MagicMock()
    db.execute = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv

    db.execute.return_value = result

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/conversations/session/session-123",
        )

    assert response.status_code == 200

    body = response.json()

    assert body["session_id"] == "session-123"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_conversation_not_found():

    db = MagicMock()
    db.execute = AsyncMock()

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
        response = await client.get(
            f"/api/v1/conversations/{uuid4()}",
        )

    assert response.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_conversation():

    conv = make_conversation()

    db = MagicMock()
    db.execute = AsyncMock()

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv

    db.execute.return_value = result

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/v1/conversations/{conv.id}",
        )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == str(conv.id)
    assert body["session_id"] == conv.session_id

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_conversations():

    db = MagicMock()
    db.execute = AsyncMock()

    conv = make_conversation()

    result = MagicMock()

    result.scalars.return_value.all.return_value = [
        conv,
    ]

    db.execute.return_value = result

    async def override_db():
        yield db

    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/conversations/",
        )

    assert response.status_code == 200

    body = response.json()

    assert len(body) == 1
    assert body[0]["session_id"] == "session-1"

    app.dependency_overrides.clear()
