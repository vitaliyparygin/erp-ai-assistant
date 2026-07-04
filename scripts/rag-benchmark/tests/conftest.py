"""Shared pytest fixtures for the rag_benchmark test suite."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def dataset_dir(tmp_path: Path) -> Path:
    """A temporary dataset directory populated with sample text documents."""
    root = tmp_path / "datasets"
    root.mkdir()

    (root / "invoice_001.txt").write_text(
        "INVOICE\n"
        "Invoice Number: INV-1001\n"
        "Bill To: Acme Corp\n"
        "Total Due: $1,250.00\n"
        "Currency: USD\n",
        encoding="utf-8",
    )

    (root / "vendor_globex.txt").write_text(
        "VENDOR PROFILE\n"
        "Vendor Name: Globex Industries\n"
        "Phone: +1-555-0100\n"
        "Email: contact@globex.example\n"
        "Address: 42 Industrial Way, Springfield\n",
        encoding="utf-8",
    )

    nested = root / "nested"
    nested.mkdir()
    (nested / "notes.md").write_text("# Random notes\nNothing structured here.\n", encoding="utf-8")

    # An unsupported format that must be skipped by the scanner.
    (root / "image.png").write_bytes(b"\x89PNG\r\n")

    return root
