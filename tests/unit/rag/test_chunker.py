from unittest.mock import MagicMock
from app.ingestion.metadata_extractor import MetadataExtractor
import pytest
from app.rag.chunker import TextChunk
import uuid
from rules.models import DocumentType
from app.rag.chunker import ParsedDocument, DocumentChunker


def test_chunk_overlap():
    chunker = DocumentChunker(
        chunk_size=500,
        chunk_overlap=100,
    )

    assert chunker.chunk_size == 500
    assert chunker.chunk_overlap == 100


def test_chunk_large_page_creates_multiple_chunks(monkeypatch):
    chunker = DocumentChunker()

    monkeypatch.setattr(
        chunker._splitter,
        "split_text",
        lambda _: [
            "one",
            "two",
            "three",
        ],
    )

    monkeypatch.setattr(
        "app.rag.chunker.MetadataExtractor.extract",
        lambda *_: {},
    )

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "big text",
                "metadata": {},
            }
        ],
        total_pages=1,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(
        document=document,
        document_id="1",
    )

    assert len(chunks) == 3
    assert [c.chunk_index for c in chunks] == [0, 1, 2]


def test_chunk_uses_recursive_splitter(monkeypatch):
    chunker = DocumentChunker()

    called = False

    def fake_split(text):
        nonlocal called
        called = True
        return ["a", "b"]

    monkeypatch.setattr(
        chunker._splitter,
        "split_text",
        fake_split,
    )

    monkeypatch.setattr(
        "app.rag.chunker.MetadataExtractor.extract",
        lambda *_: {},
    )

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "abc",
                "metadata": {},
            }
        ],
        total_pages=1,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunker.chunk(
        document=document,
        document_id="1",
    )

    assert called is True


def test_chunk_skips_blank_split(monkeypatch):
    chunker = DocumentChunker()

    monkeypatch.setattr(
        chunker._splitter,
        "split_text",
        lambda _: [
            "",
            "   ",
            "chunk",
        ],
    )

    monkeypatch.setattr(
        "app.rag.chunker.MetadataExtractor.extract",
        lambda *_: {},
    )

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "text",
                "metadata": {},
            }
        ],
        total_pages=1,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(
        document=document,
        document_id="1",
    )

    assert len(chunks) == 1
    assert chunks[0].content == "chunk"


def test_chunk_document_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.rag.chunker.MetadataExtractor.extract",
        lambda *_: {
            "document_type": "Invoice",
            "invoice_number": "INV-1",
        },
    )

    chunker = DocumentChunker()

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "invoice",
                "metadata": {},
            }
        ],
        total_pages=1,
        file_path="invoice.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(
        document=document,
        document_id="1",
    )

    metadata = chunks[0].metadata

    assert metadata["document_type"] == "Invoice"
    assert metadata["invoice_number"] == "INV-1"


def test_chunk_metadata_contains_document_id():
    chunker = DocumentChunker()

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "hello",
                "metadata": {},
            }
        ],
        total_pages=1,
        file_path="/tmp/doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(
        document=document,
        document_id="doc-123",
    )

    metadata = chunks[0].metadata

    assert metadata["document_id"] == "doc-123"
    assert metadata["file_path"] == "/tmp/doc.pdf"
    assert metadata["mime_type"] == "application/pdf"


def test_chunk_custom_metadata():
    chunker = DocumentChunker()

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "hello",
                "metadata": {
                    "section": "A",
                },
            }
        ],
        total_pages=1,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(document, "doc1")

    assert chunks[0].metadata["section"] == "A"


def test_estimate_tokens():
    chunker = DocumentChunker()

    assert chunker.estimate_tokens("abcd") == 1
    assert chunker.estimate_tokens("abcdefgh") == 2
    assert chunker.estimate_tokens("") == 1


def test_chunk_indexes_are_incremental():
    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=0,
    )

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "one",
                "metadata": {},
            },
            {
                "page_number": 2,
                "text": "two",
                "metadata": {},
            },
        ],
        total_pages=2,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(document, "doc1")

    assert [c.chunk_index for c in chunks] == [0, 1]


def test_chunk_multiple_pages():
    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=0,
    )

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "page1",
                "metadata": {},
            },
            {
                "page_number": 2,
                "text": "page2",
                "metadata": {},
            },
        ],
        total_pages=2,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(document, "doc1")

    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2


def test_chunk_single_page():
    chunker = DocumentChunker(
        chunk_size=100,
        chunk_overlap=0,
    )

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "hello world",
                "metadata": {},
            }
        ],
        total_pages=1,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(document, "doc1")

    assert len(chunks) == 1
    assert chunks[0].content == "hello world"


def test_chunk_skips_blank_pages():
    chunker = DocumentChunker()

    document = ParsedDocument(
        pages=[
            {
                "page_number": 1,
                "text": "",
                "metadata": {},
            },
            {
                "page_number": 2,
                "text": "hello world",
                "metadata": {},
            },
        ],
        total_pages=2,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(document, "doc1")

    assert len(chunks) == 1
    assert chunks[0].page_number == 2


def test_chunk_empty_document():
    chunker = DocumentChunker()

    document = ParsedDocument(
        pages=[],
        total_pages=0,
        file_path="doc.pdf",
        mime_type="application/pdf",
    )

    chunks = chunker.chunk(document, "doc1")

    assert chunks == []


def test_parsed_document_defaults():
    doc = ParsedDocument(
        pages=[],
        total_pages=0,
        file_path="a.pdf",
        mime_type="application/pdf",
    )

    assert doc.document_metadata == {}


def test_text_chunk_id_is_uuid():
    chunk = TextChunk(
        content="abc",
        chunk_index=0,
    )

    uuid.UUID(chunk.id)


def test_text_chunk_len():
    chunk = TextChunk(
        content="abcdef",
        chunk_index=0,
    )

    assert len(chunk) == 6


def test_extract_regex_without_group(monkeypatch):
    definition = MagicMock()
    definition.name = "currency"
    definition.patterns = [r"USD"]

    monkeypatch.setattr(
        "app.parsers.field_dictionary.FIELD_DEFINITIONS",
        {"currency": definition},
    )

    monkeypatch.setattr(
        "rules.detect_document_type",
        lambda **_: None,
    )

    metadata = MetadataExtractor.extract(
        "Currency USD",
        "a.pdf",
    )

    assert metadata["currency"] == "USD"


def test_extract_regex_group(monkeypatch):
    definition = MagicMock()
    definition.name = "invoice_number"
    definition.patterns = [r"Invoice:\s*(\d+)"]

    monkeypatch.setattr(
        "app.parsers.field_dictionary.FIELD_DEFINITIONS",
        {"invoice": definition},
    )

    monkeypatch.setattr(
        "rules.detect_document_type",
        lambda **_: None,
    )

    metadata = MetadataExtractor.extract(
        "Invoice: 12345",
        "a.pdf",
    )

    assert metadata["invoice_number"] == "12345"


@pytest.mark.asyncio
async def test_extract_document_type(monkeypatch):
    monkeypatch.setattr(
        "rules.detect_document_type",
        lambda **_: "invoice",
    )

    monkeypatch.setattr(
        "app.parsers.field_dictionary.FIELD_DEFINITIONS",
        {},
    )

    metadata = MetadataExtractor.extract(
        "invoice",
        "invoice.pdf",
    )

    assert metadata["document_name"] == "invoice.pdf"
    assert metadata["document_type"] == DocumentType.INVOICE


@pytest.mark.asyncio
async def test_extract_only_document_name_when_no_matches(monkeypatch):
    monkeypatch.setattr(
        "rules.detect_document_type",
        lambda **_: None,
    )

    metadata = MetadataExtractor.extract(
        "just random text",
        "file.pdf",
    )

    assert metadata == {
        "document_name": "file.pdf",
    }
