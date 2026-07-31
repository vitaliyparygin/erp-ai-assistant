import pytest
from fastapi import Response
from unittest.mock import AsyncMock, MagicMock

from app.main import (
    lifespan,
    request_context_middleware,
    health_check,
    root,
    global_exception_handler,
)


@pytest.mark.asyncio
async def test_lifespan(monkeypatch):
    setup_logging = MagicMock()
    create_tables = AsyncMock()
    app_info = MagicMock()
    logger = MagicMock()

    monkeypatch.setattr("app.main.setup_logging", setup_logging)
    monkeypatch.setattr("app.main.create_tables", create_tables)
    monkeypatch.setattr("app.main.APP_INFO", app_info)
    monkeypatch.setattr("app.main.logger", logger)

    async with lifespan(None):
        pass

    setup_logging.assert_called_once()
    create_tables.assert_awaited_once()
    app_info.info.assert_called_once()


@pytest.mark.asyncio
async def test_request_context_middleware():
    request = MagicMock()

    async def call_next(req):
        return Response(status_code=200)

    response = await request_context_middleware(request, call_next)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_request_context_middleware_exception():
    request = MagicMock()

    async def call_next(req):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await request_context_middleware(request, call_next)


@pytest.mark.asyncio
async def test_global_exception_handler():
    request = MagicMock()

    response = await global_exception_handler(
        request,
        Exception("boom"),
    )

    assert response.status_code == 500
    assert b"boom" in response.body


@pytest.mark.asyncio
async def test_health():
    result = await health_check()

    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_root():
    result = await root()

    assert "service" in result
    assert "version" in result
    assert result["docs"] == "/docs"
