"""
Structured JSON logging using structlog.
Production-grade logging with context binding, trace IDs, and log levels.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


def add_app_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject application context into every log record."""
    from app.core.config import get_settings
    settings = get_settings()
    event_dict["app"] = settings.app_name
    event_dict["version"] = settings.app_version
    event_dict["env"] = settings.app_env
    return event_dict


def setup_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """
    Configure structlog for structured, production-ready logging.

    In development: human-readable colored console output.
    In production: JSON output suitable for log aggregators (Datadog, ELK, etc.).
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=False,),
        add_app_context,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.ExceptionRenderer(),
    ]

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)  # type: ignore[assignment]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "openai", "langchain", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a bound logger for a module."""
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding structured log fields within a scope."""

    def __init__(self, **kwargs: Any) -> None:
        self.fields = kwargs

    def __enter__(self) -> "LogContext":
        structlog.contextvars.bind_contextvars(**self.fields)
        return self

    def __exit__(self, *args: Any) -> None:
        structlog.contextvars.unbind_contextvars(*self.fields.keys())


def bind_request_context(
    request_id: str,
    path: str,
    method: str,
    user_id: str | None = None,
) -> None:
    """Bind request-scoped context for all log statements within the request."""
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        path=path,
        method=method,
        **({"user_id": user_id} if user_id else {}),
    )


def clear_request_context() -> None:
    """Clear request-scoped context after the request completes."""
    structlog.contextvars.clear_contextvars()