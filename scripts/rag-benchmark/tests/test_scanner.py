"""Tests for rag_benchmark.scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from rag_benchmark.models import DocumentFormat
from rag_benchmark.scanner import DocumentScanner, detect_format


def test_detect_format_maps_known_extensions() -> None:
    assert detect_format(Path("a.pdf")) is DocumentFormat.PDF
    assert detect_format(Path("a.docx")) is DocumentFormat.DOCX
    assert detect_format(Path("a.txt")) is DocumentFormat.TXT
    assert detect_format(Path("a.md")) is DocumentFormat.MARKDOWN
    assert detect_format(Path("a.markdown")) is DocumentFormat.MARKDOWN


def test_detect_format_unknown_extension() -> None:
    assert detect_format(Path("a.png")) is DocumentFormat.UNKNOWN


def test_scan_recursive_finds_supported_files_and_skips_unsupported(dataset_dir: Path) -> None:
    scanner = DocumentScanner(recursive=True)
    results = scanner.scan(dataset_dir)

    names = {r.path.name for r in results}
    assert "invoice_001.txt" in names
    assert "vendor_globex.txt" in names
    assert "notes.md" in names  # found via recursion into nested/
    assert "image.png" not in names  # unsupported format skipped


def test_scan_non_recursive_skips_nested_files(dataset_dir: Path) -> None:
    scanner = DocumentScanner(recursive=False)
    results = scanner.scan(dataset_dir)

    names = {r.path.name for r in results}
    assert "notes.md" not in names
    assert "invoice_001.txt" in names


def test_scan_missing_directory_raises(tmp_path: Path) -> None:
    scanner = DocumentScanner()
    with pytest.raises(FileNotFoundError):
        scanner.scan(tmp_path / "does_not_exist")


def test_scan_file_instead_of_directory_raises(tmp_path: Path) -> None:
    file_path = tmp_path / "file.txt"
    file_path.write_text("hi", encoding="utf-8")
    scanner = DocumentScanner()
    with pytest.raises(NotADirectoryError):
        scanner.scan(file_path)
