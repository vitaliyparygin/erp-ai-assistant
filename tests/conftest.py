import pytest
from app.agents.state import AgentState
from types import SimpleNamespace
from unittest.mock import MagicMock
from app.models.schemas import RetrievedChunk


def make_chunk(
    *,
    score: float = 0.5,
    content: str = "text",
    document_name: str = "doc.pdf",
    chunk_index: int = 0,
):
    return RetrievedChunk(
        chunk_id=str(chunk_index),
        document_id="doc-id",
        document_name=document_name,
        content=content,
        page_number=1,
        chunk_index=chunk_index,
        score=score,
        metadata={},
    )


class FakeAsyncSession:
    def __init__(self, document):
        self.document = document

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def begin(self):
        return self

    async def execute(self, *args, **kwargs):
        result = MagicMock()
        result.scalar_one_or_none.return_value = self.document
        return result

    async def commit(self):
        pass

    def add(self, *_):
        pass

    @property
    def bind(self):
        return object()


class FakeExecuteResult:
    def __init__(self, document):
        self._document = document

    def scalar_one_or_none(self):
        return self._document


def patch_db(monkeypatch, session):
    monkeypatch.setattr(
        "app.db.session.get_sessionmaker",
        lambda: FakeSessionFactory(session),
    )


def make_parsed_document():
    return SimpleNamespace(
        total_pages=3,
    )


class FakeBeginContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSessionFactory:
    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session

    def begin(self):
        return self.session


@pytest.fixture
def agent_state():
    return AgentState(
        session_id="1",
        query="test",
        original_query="test",
        retrieved_chunks=[],
        reranked_chunks=[],
        citations=[],
        messages=[],
        research_notes=[],
        execution_path=[],
        agent_trace={},
    )
