"""Small shared utilities: logging setup, id/slug helpers, text helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

def stable_document_id(path: Path) -> str:
    """Derive a short, stable, content-independent id from a file path.

    Uses the absolute path string so the same file always yields the same id
    across runs, which keeps generated benchmark ids reproducible.
    """
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()
    return digest[:12]