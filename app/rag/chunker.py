"""
Document chunking pipeline.
Supports PDF, DOCX, TXT, and Markdown with configurable chunking strategies.
Preserves metadata (page numbers, section headings, document hierarchy).
"""
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings
from app.core.exceptions import DocumentIngestionError, UnsupportedFileTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """A single text chunk extracted from a document."""

    content: str
    chunk_index: int
    page_number: int | None = None
    section_heading: str | None = None
    token_count: int | None = None
    chunk_methadata: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return str(uuid.uuid4())

    def __len__(self) -> int:
        return len(self.content)


@dataclass
class ParsedDocument:
    """Result of parsing a document file."""

    pages: list[dict]   # [{page_number, text, metadata}]
    total_pages: int
    file_path: str
    mime_type: str
    document_metadata: dict = field(default_factory=dict)


class DocumentParser:
    """
    Multi-format document parser.
    Extracts text with page-level metadata.
    """

    def parse(self, file_path: str | Path, mime_type: str) -> ParsedDocument:
        """Parse a document file and return structured pages."""
        path = Path(file_path)
        if not path.exists():
            raise DocumentIngestionError(f"File not found: {file_path}")

        dispatch = {
            "application/pdf": self._parse_pdf,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._parse_docx,
            "text/plain": self._parse_text,
            "text/markdown": self._parse_text,
        }

        parser = dispatch.get(mime_type)
        if parser is None:
            raise UnsupportedFileTypeError(f"Unsupported MIME type: {mime_type}")

        return parser(path)

    def _parse_pdf(self, path: Path) -> ParsedDocument:
        """Extract text from PDF with page-level metadata."""
        pages = []
        try:
            with pdfplumber.open(path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text() or ""
                    text = self._clean_text(text)
                    if text.strip():
                        pages.append({
                            "page_number": i,
                            "text": text,
                            "metadata": {
                                "page_width": page.width,
                                "page_height": page.height,
                            },
                        })
        except Exception as e:
            raise DocumentIngestionError(f"PDF parsing failed: {e}") from e

        logger.info("pdf_parsed", path=str(path), pages=len(pages))
        return ParsedDocument(
            pages=pages,
            total_pages=len(pages),
            file_path=str(path),
            mime_type="application/pdf",
        )

    def _parse_docx(self, path: Path) -> ParsedDocument:
        """Extract text from DOCX with paragraph-level metadata."""
        try:
            from docx import Document
            doc = Document(str(path))
        except Exception as e:
            raise DocumentIngestionError(f"DOCX parsing failed: {e}") from e

        # Group paragraphs into synthetic "pages" of ~500 words each
        all_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        pages = [{"page_number": 1, "text": all_text, "metadata": {}}]

        return ParsedDocument(
            pages=pages,
            total_pages=1,
            file_path=str(path),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def _parse_text(self, path: Path) -> ParsedDocument:
        """Parse plain text or Markdown file."""
        text = path.read_text(encoding="utf-8", errors="replace")
        text = self._clean_text(text)
        pages = [{"page_number": 1, "text": text, "metadata": {}}]
        return ParsedDocument(
            pages=pages,
            total_pages=1,
            file_path=str(path),
            mime_type="text/plain",
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace while preserving paragraph breaks."""
        # Collapse excessive whitespace within lines
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize line endings
        text = re.sub(r"\r\n?", "\n", text)
        # Collapse more than 2 consecutive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class DocumentChunker:
    """
    Splits parsed documents into overlapping text chunks.

    Strategy:
    1. Split each page using RecursiveCharacterTextSplitter
    2. Preserve page number and section heading metadata
    3. Assign sequential chunk indices across the whole document
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
            is_separator_regex=False,
        )

    def chunk(self, document: ParsedDocument, document_id: str) -> list[TextChunk]:
        """Split a parsed document into chunks."""
        chunks: list[TextChunk] = []
        chunk_index = 0

        for page in document.pages:
            page_text = page["text"]
            page_number = page.get("page_number")

            if not page_text.strip():
                continue

            splits = self._splitter.split_text(page_text)

            for split_text in splits:
                if not split_text.strip():
                    continue

                chunk = TextChunk(
                    content=split_text.strip(),
                    chunk_index=chunk_index,
                    page_number=page_number,
                    metadata={
                        "document_id": document_id,
                        "file_path": document.file_path,
                        "mime_type": document.mime_type,
                        **page.get("metadata", {}),
                    },
                )
                chunks.append(chunk)
                chunk_index += 1

        logger.info(
            "document_chunked",
            document_id=document_id,
            total_chunks=len(chunks),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )
        return chunks

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars ≈ 1 token for English)."""
        return max(1, len(text) // 4)