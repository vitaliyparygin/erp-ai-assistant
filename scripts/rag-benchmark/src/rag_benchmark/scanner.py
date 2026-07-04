"""Filesystem scanning: discover candidate documents in a dataset directory."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rag_benchmark.models import DocumentFormat, ScannedFile
from rag_benchmark.utils import get_logger

logger = get_logger("scanner")

_EXTENSION_MAP: dict[str, DocumentFormat] = {
    ".pdf": DocumentFormat.PDF,
    ".docx": DocumentFormat.DOCX,
    ".txt": DocumentFormat.TXT,
    ".md": DocumentFormat.MARKDOWN,
    ".markdown": DocumentFormat.MARKDOWN,
}


def detect_format(path: Path) -> DocumentFormat:
    """Map a file's extension to a DocumentFormat.

    Args:
        path: File path to inspect.

    Returns:
        The matching DocumentFormat, or UNKNOWN if unsupported.
    """
    return _EXTENSION_MAP.get(path.suffix.lower(), DocumentFormat.UNKNOWN)


class DocumentScanner:
    """Discovers files within a dataset directory that can be read.

    Kept deliberately dumb: it only lists files and tags their format. All
    interpretation (reading, classifying) happens in later pipeline stages,
    keeping this class single-responsibility and easy to test.
    """

    def __init__(self, recursive: bool = True) -> None:
        self._recursive = recursive

    def scan(self, dataset_dir: Path) -> list[ScannedFile]:
        """Scan a directory and return all supported files found.

        Args:
            dataset_dir: Root directory to scan.

        Returns:
            A list of ScannedFile entries, sorted by path for determinism.

        Raises:
            FileNotFoundError: If dataset_dir does not exist.
            NotADirectoryError: If dataset_dir is not a directory.
        """
        dataset_dir = Path(dataset_dir)
        if not dataset_dir.exists():
            raise FileNotFoundError(f"Dataset directory not found: {dataset_dir}")
        if not dataset_dir.is_dir():
            raise NotADirectoryError(f"Not a directory: {dataset_dir}")

        pattern = "**/*" if self._recursive else "*"
        results: list[ScannedFile] = []

        for candidate in sorted(dataset_dir.glob(pattern)):
            if not candidate.is_file():
                continue
            fmt = detect_format(candidate)
            if fmt is DocumentFormat.UNKNOWN:
                logger.debug("Skipping unsupported file: %s", candidate)
                continue
            stat = candidate.stat()
            results.append(
                ScannedFile(
                    path=candidate,
                    format=fmt,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                )
            )

        logger.info("Scanned %s: found %d supported file(s)", dataset_dir, len(results))
        return results
