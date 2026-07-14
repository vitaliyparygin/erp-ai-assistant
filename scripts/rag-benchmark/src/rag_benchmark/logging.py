"""Small shared utilities: logging setup, id/slug helpers, text helpers."""

from __future__ import annotations

import logging

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

    level = logging.DEBUG if verbose else logging.INFO

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
    logging.getLogger()
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)
