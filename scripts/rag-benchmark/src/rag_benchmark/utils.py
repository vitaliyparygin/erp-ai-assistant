"""Small shared utilities: logging setup, id/slug helpers, text helpers."""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path

_LOGGER_NAME = "rag_benchmark"


def configure_logging(verbose: bool = False, debug: bool = False) -> logging.Logger:
    """Configure and return the package-wide logger.

    Args:
        verbose: If True, set level to INFO.
        debug: If True, set level to DEBUG (overrides verbose).

    Returns:
        The configured logger instance.
    """
    logger = logging.getLogger(_LOGGER_NAME)
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING

    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        for handler in logger.handlers:
            handler.setLevel(level)

    # pdfminer (used internally by pdfplumber) logs a WARNING for every
    # malformed font descriptor, embedded font quirk, etc. it encounters.
    # These are almost never actionable for benchmark generation, so they
    # are silenced unless --debug is explicitly requested.
    logging.getLogger("pdfminer").setLevel(logging.DEBUG if debug else logging.ERROR)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger of the package logger."""
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def stable_document_id(path: Path) -> str:
    """Derive a short, stable, content-independent id from a file path.

    Uses the absolute path string so the same file always yields the same id
    across runs, which keeps generated benchmark ids reproducible.
    """
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()
    return digest[:12]


def slugify(value: str) -> str:
    """Convert a string into a filesystem/tag-safe lowercase slug."""
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^\w\s-]", "", normalized).strip().lower()
    return re.sub(r"[-\s]+", "-", normalized)


def truncate(text: str, max_chars: int = 200) -> str:
    """Truncate text to max_chars, appending an ellipsis if shortened."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "\u2026"


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace and strip the result."""
    return re.sub(r"\s+", " ", text).strip()