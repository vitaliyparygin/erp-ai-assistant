import pytest
from app.models.schemas import Citation
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, Mock
from types import SimpleNamespace
from app.main import app
from app.api.v1.chat import get_agent_graph
from app.core.dependencies import (
    get_db_session,
    get_qdrant_client,
    get_redis_client,
)
from unittest.mock import MagicMock
from uuid import uuid4
from app.agents.citation import CitationAgent
from tests.factories import make_state
from app.models.schemas import RetrievedChunk


@pytest.mark.asyncio
async def test_chat_success():

    #
    # graph
    #
    graph = AsyncMock()

    graph.run.return_value = AsyncMock(
        final_answer="Invoice total is 1000 USD",
        citations=[],
        input_tokens=40,
        output_tokens=83,
        total_tokens=123,
        execution_path=[],
        agent_trace={},
    )

    #
    # fake db
    #
    db = MagicMock()

    db.execute = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    #
    # _get_or_create_session()
    #
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result

    #
    # overrides
    #
    async def override_graph():
        return graph

    async def override_db():
        yield db

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    app.dependency_overrides[get_agent_graph] = override_graph
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/chat/",
            json={
                "message": "invoice total",
                "session_id": "1",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()

    assert data["answer"] == "Invoice total is 1000 USD"


@pytest.mark.asyncio
async def test_chat_returns_citations():

    graph = AsyncMock()

    graph.run.return_value = SimpleNamespace(
        final_answer="answer",
        citations=[
            Citation(
                document_id=str(uuid4()),
                document_name="Invoice.pdf",
                page_number=5,
                chunk_index=0,
                chunk_content="Invoice total is 1000 USD",
                relevance_score=0.97,
            )
        ],
        input_tokens=40,
        output_tokens=83,
        total_tokens=123,
        execution_path=[],
        agent_trace={},
    )

    db = MagicMock()
    db.execute = AsyncMock()

    conv = SimpleNamespace(id=uuid4())

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv
    db.execute.return_value = result

    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def override_graph():
        return graph

    async def override_db():
        yield db

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    app.dependency_overrides[get_agent_graph] = override_graph
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/chat/",
            json={
                "message": "invoice",
                "session_id": "1",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200

    body = response.json()

    assert len(body["citations"]) == 1
    assert body["citations"][0]["document_name"] == "Invoice.pdf"
    assert body["total_tokens"] == 123


@pytest.mark.asyncio
async def test_graph_failure():

    graph = AsyncMock()
    graph.run.side_effect = RuntimeError("graph exploded")

    db = MagicMock()
    db.execute = AsyncMock()

    conv = SimpleNamespace(id=uuid4())

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv
    db.execute.return_value = result

    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def override_graph():
        return graph

    async def override_db():
        yield db

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    app.dependency_overrides[get_agent_graph] = override_graph
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/chat/",
            json={
                "message": "invoice",
                "session_id": "1",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 500
    assert "Agent pipeline failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_stream_success():

    graph = AsyncMock()
    db = MagicMock()
    db.execute = AsyncMock()

    conv = SimpleNamespace(id=uuid4())

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv
    db.execute.return_value = result

    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def fake_stream(state):
        yield {"event": "on_chain_start", "data": {"name": "research"}}

        yield {
            "event": "on_chain_end",
            "data": {"name": "summarizer", "output": {"final_answer": "Hello world"}},
        }

    graph.stream = fake_stream

    app.dependency_overrides[get_agent_graph] = lambda: graph

    async def override_graph():
        return graph

    async def override_db():
        yield db

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    app.dependency_overrides[get_agent_graph] = override_graph
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/chat/stream",
            params={
                "message": "invoice",
                "session_id": "1",
            },
        )
    assert response.status_code == 200
    text = response.text

    assert "connected" in text
    assert "agent_start" in text
    assert "token" in text
    assert "done" in text
    assert "Hello world" in text


@pytest.mark.asyncio
async def test_citation_agent_empty():

    agent = CitationAgent(llm=AsyncMock())

    state = make_state(final_answer=None, reranked_chunks=[])

    result = await agent(state)

    assert result["citations"] == []
    assert result["execution_path"] == ["citation"]


@pytest.mark.asyncio
async def test_citation_agent_extracts():

    agent = CitationAgent(llm=AsyncMock())

    chunk = RetrievedChunk(
        chunk_id="1",
        document_id="00000000-0000-0000-0000-000000000001",
        document_name="Invoice.pdf",
        content="Invoice total is 1000 USD",
        page_number=5,
        score=0.95,
        chunk_index=0,
        metadata={},
    )

    state = make_state(
        final_answer="answer",
        reranked_chunks=[chunk],
    )

    result = await agent(state)

    assert len(result["citations"]) == 1

    citation = result["citations"][0]

    assert citation.document_name == "Invoice.pdf"
    assert citation.page_number == 5
    assert citation.relevance_score == 0.95


@pytest.mark.asyncio
async def test_chat_stream_error():

    graph = AsyncMock()

    async def fake_stream(state):
        raise RuntimeError("boom")
        yield  # щоб це був async generator

    graph.stream = fake_stream

    db = MagicMock()
    db.execute = AsyncMock()

    conv = SimpleNamespace(id=uuid4())

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv
    db.execute.return_value = result

    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def override_graph():
        return graph

    async def override_db():
        yield db

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    app.dependency_overrides[get_agent_graph] = override_graph
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/chat/stream",
            params={
                "message": "invoice",
                "session_id": "1",
            },
        )

    assert response.status_code == 200
    assert "error" in response.text
    assert "boom" in response.text


@pytest.mark.asyncio
async def test_chat_stream_without_summary():

    graph = AsyncMock()

    async def fake_stream(state):

        yield {
            "event": "on_chain_start",
            "data": {
                "name": "retriever",
            },
        }

        yield {
            "event": "on_chain_end",
            "data": {
                "name": "retriever",
                "output": {},
            },
        }

    graph.stream = fake_stream

    db = MagicMock()
    db.execute = AsyncMock()

    conv = SimpleNamespace(id=uuid4())

    result = MagicMock()
    result.scalar_one_or_none.return_value = conv
    db.execute.return_value = result

    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def override_graph():
        return graph

    async def override_db():
        yield db

    async def override_redis():
        yield AsyncMock()

    async def override_qdrant():
        yield AsyncMock()

    app.dependency_overrides[get_agent_graph] = override_graph
    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis_client] = override_redis
    app.dependency_overrides[get_qdrant_client] = override_qdrant

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/chat/stream",
            params={
                "message": "invoice",
                "session_id": "1",
            },
        )

    assert response.status_code == 200
    assert "connected" in response.text
    assert "agent_start" in response.text
    assert "agent_end" in response.text
    assert "done" in response.text
    assert "token" not in response.text
