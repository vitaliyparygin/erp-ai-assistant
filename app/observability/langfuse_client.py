"""
LangFuse observability integration.
Tracks agent traces, token usage, latency, and evaluation scores.
"""

from typing import Any, cast

from app.core.logging import get_logger

logger = get_logger(__name__)


class LangFuseTracer:  # pragma: no cover
    """
    Wraps LangFuse SDK for structured observability.
    Provides trace/span context managers for agent nodes.

    Falls back to no-op mode if LangFuse is disabled or credentials are missing.
    """

    def __init__(
        self, enabled: bool, secret_key: str, public_key: str, host: str
    ) -> None:  # pragma: no cover
        self._enabled = enabled
        self._client = None

        if enabled and secret_key and public_key:
            try:
                from langfuse import Langfuse

                self._client = cast(
                    Any,
                    Langfuse(
                        secret_key=secret_key,
                        public_key=public_key,
                        host=host,
                        debug=False,
                    ),
                )
                logger.info("langfuse_initialized", host=host)
            except ImportError:
                logger.warning("langfuse_not_installed")
            except Exception as e:
                logger.warning("langfuse_init_failed", error=str(e))

    @property
    def is_active(self) -> bool:  # pragma: no cover
        return self._client is not None

    def trace(
        self,
        name: str,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:  # pragma: no cover
        """Start a new trace."""
        if not self._client:
            return _NoOpTrace()

        return self._client.trace(
            name=name,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
        )

    def log_generation(
        self,
        trace: Any,
        name: str,
        model: str,
        prompt: str,
        completion: str,
        usage: dict[str, int] | None = None,
        latency_ms: float | None = None,
    ) -> None:  # pragma: no cover
        """Log an LLM generation within a trace."""
        if not self._client or not trace or isinstance(trace, _NoOpTrace):
            return

        try:
            trace.generation(
                name=name,
                model=model,
                prompt=prompt,
                completion=completion,
                usage=usage,
                metadata={"latency_ms": latency_ms},
            )
        except Exception as e:
            logger.error("langfuse_log_generation_error", error=str(e))

    def log_score(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: str | None = None,
    ) -> None:  # pragma: no cover
        """Attach an evaluation score to a trace."""
        if not self._client:
            return

        try:
            self._client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment,
            )
        except Exception as e:
            logger.error("langfuse_log_score_error", error=str(e))

    def flush(self) -> None:  # pragma: no cover
        """Flush pending events to LangFuse."""
        if self._client:
            try:
                self._client.flush()
            except Exception:
                import traceback

                traceback.print_exc()
                raise


class _NoOpTrace:  # pragma: no cover
    """No-op trace object used when LangFuse is disabled."""

    def span(self, *args: Any, **kwargs: Any) -> "_NoOpTrace":
        return self

    def generation(self, *args: Any, **kwargs: Any) -> "_NoOpTrace":
        return self

    def update(self, *args: Any, **kwargs: Any) -> "_NoOpTrace":
        return self

    def end(self, *args: Any, **kwargs: Any) -> None:
        pass

    @property
    def id(self) -> str:
        return ""


def get_langfuse_client(settings: Any) -> LangFuseTracer:  # pragma: no cover
    """Factory — returns a tracer configured from app settings."""
    return LangFuseTracer(
        enabled=settings.langfuse_enabled,
        secret_key=settings.langfuse_secret_key,
        public_key=settings.langfuse_public_key,
        host=settings.langfuse_host,
    )
