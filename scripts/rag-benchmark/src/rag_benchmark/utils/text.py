from __future__ import annotations
import re
import unicodedata

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