from app.core.exceptions import UnsupportedFileTypeError
import pytest
from app.core.exceptions import DocumentIngestionError
from unittest.mock import MagicMock
from app.rag.chunker import DocumentParser


def test_parse_docx_success(monkeypatch, tmp_path):
    paragraph1 = MagicMock(text="hello")
    paragraph2 = MagicMock(text="world")

    fake_doc = MagicMock(
        paragraphs=[paragraph1, paragraph2],
    )

    monkeypatch.setattr(
        "docx.Document",
        lambda *_: fake_doc,
    )

    file = tmp_path / "doc.docx"
    file.write_text("")

    parser = DocumentParser()

    result = parser.parse(
        file,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert result.total_pages == 1
    assert "hello" in result.pages[0]["text"]
    assert "world" in result.pages[0]["text"]


def test_parse_docx_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "docx.Document",
        lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    file = tmp_path / "doc.docx"
    file.write_text("")

    parser = DocumentParser()

    with pytest.raises(DocumentIngestionError):
        parser.parse(
            file,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )


def test_parse_markdown(tmp_path):
    file = tmp_path / "doc.md"
    file.write_text(
        "# Header\ntext",
        encoding="utf-8",
    )

    parser = DocumentParser()

    result = parser.parse(
        file,
        "text/markdown",
    )

    assert result.total_pages == 1
    assert result.pages[0]["text"] == "# Header\ntext"


def test_parse_text(tmp_path):
    file = tmp_path / "doc.txt"
    file.write_text(
        "hello\n\nworld",
        encoding="utf-8",
    )

    parser = DocumentParser()

    result = parser.parse(
        file,
        "text/plain",
    )

    assert result.total_pages == 1
    assert result.pages[0]["text"] == "hello\n\nworld"
    assert result.mime_type == "text/plain"


def test_clean_text():
    text = "abc   def\r\n\r\n\r\nxyz\t\t123"

    cleaned = DocumentParser._clean_text(text)

    assert cleaned == "abc def\n\nxyz 123"


def test_parse_unsupported_type(tmp_path):
    file = tmp_path / "file.bin"
    file.write_bytes(b"123")

    parser = DocumentParser()

    with pytest.raises(UnsupportedFileTypeError):
        parser.parse(
            file,
            "application/octet-stream",
        )


def test_parse_file_not_found(tmp_path):
    parser = DocumentParser()

    with pytest.raises(DocumentIngestionError):
        parser.parse(
            tmp_path / "missing.pdf",
            "application/pdf",
        )
