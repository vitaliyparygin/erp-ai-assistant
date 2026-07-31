from unittest.mock import MagicMock
import pytest
from app.core.exceptions import DocumentIngestionError
from app.rag.chunker import DocumentParser


def test_parse_dispatch_pdf(monkeypatch, tmp_path):
    parser = DocumentParser()

    called = False

    def fake(path):
        nonlocal called
        called = True
        return "ok"

    monkeypatch.setattr(
        parser,
        "_parse_pdf",
        fake,
    )

    file = tmp_path / "a.pdf"
    file.write_text("")

    result = parser.parse(
        file,
        "application/pdf",
    )

    assert called is True
    assert result == "ok"


def test_parse_pdf_failure(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "pdfplumber.open",
        lambda *_: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    file = tmp_path / "doc.pdf"
    file.write_text("")

    parser = DocumentParser()

    with pytest.raises(DocumentIngestionError):
        parser.parse(
            file,
            "application/pdf",
        )


def test_parse_pdf_none_text(monkeypatch, tmp_path):
    page = MagicMock()
    page.extract_text.return_value = None
    page.width = 100
    page.height = 100

    pdf = MagicMock()
    pdf.pages = [page]

    class PdfContext:
        def __enter__(self):
            return pdf

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "pdfplumber.open",
        lambda *_: PdfContext(),
    )

    file = tmp_path / "doc.pdf"
    file.write_text("")

    parser = DocumentParser()

    result = parser.parse(
        file,
        "application/pdf",
    )

    assert result.total_pages == 0
    assert result.pages == []


def test_parse_pdf_skips_empty_pages(monkeypatch, tmp_path):
    empty = MagicMock()
    empty.extract_text.return_value = ""
    empty.width = 100
    empty.height = 100

    page = MagicMock()
    page.extract_text.return_value = "content"
    page.width = 100
    page.height = 100

    pdf = MagicMock()
    pdf.pages = [empty, page]

    class PdfContext:
        def __enter__(self):
            return pdf

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "pdfplumber.open",
        lambda *_: PdfContext(),
    )

    file = tmp_path / "doc.pdf"
    file.write_text("")

    parser = DocumentParser()

    result = parser.parse(
        file,
        "application/pdf",
    )

    assert result.total_pages == 1
    assert result.pages[0]["text"] == "content"


def test_parse_pdf_success(monkeypatch, tmp_path):
    page1 = MagicMock()
    page1.extract_text.return_value = "Page one"
    page1.width = 100
    page1.height = 200

    page2 = MagicMock()
    page2.extract_text.return_value = "Page two"
    page2.width = 110
    page2.height = 210

    pdf = MagicMock()
    pdf.pages = [page1, page2]

    class PdfContext:
        def __enter__(self):
            return pdf

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        "pdfplumber.open",
        lambda *_: PdfContext(),
    )

    file = tmp_path / "doc.pdf"
    file.write_text("dummy")

    parser = DocumentParser()

    result = parser.parse(
        file,
        "application/pdf",
    )

    assert result.total_pages == 2
    assert result.pages[0]["page_number"] == 1
    assert result.pages[0]["text"] == "Page one"
    assert result.pages[1]["page_number"] == 2
    assert result.pages[1]["text"] == "Page two"
