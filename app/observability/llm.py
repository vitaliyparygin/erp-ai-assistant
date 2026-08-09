import time
from typing import Any

from langchain_core.runnables import Runnable

from app.observability.metrics import (
    LLM_REQUESTS_TOTAL,
    LLM_LATENCY_SECONDS,
    LLM_TOKENS_TOTAL,
)


class InstrumentedLLM(Runnable[Any, Any]):
    """
    Runnable wrapper around an LLM that records Prometheus metrics.

    Metrics are collected at the actual LLM layer, so every wrapped
    invocation contributes to request count, latency, and token usage.
    """

    def __init__(
        self,
        llm: Runnable[Any, Any],
        *,
        model: str,
        agent: str,
    ) -> None:
        self._llm = llm
        self._model = model
        self._agent = agent

    def invoke(
        self,
        input: Any,
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        start = time.perf_counter()

        try:
            result = self._llm.invoke(
                input,
                config=config,
                **kwargs,
            )

            LLM_REQUESTS_TOTAL.labels(
                model=self._model,
                agent=self._agent,
                status="success",
            ).inc()

            self._record_tokens(result)

            return result

        except Exception:
            LLM_REQUESTS_TOTAL.labels(
                model=self._model,
                agent=self._agent,
                status="error",
            ).inc()
            raise

        finally:
            LLM_LATENCY_SECONDS.labels(
                model=self._model,
                agent=self._agent,
            ).observe(time.perf_counter() - start)

    async def ainvoke(
        self,
        input: Any,
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        start = time.perf_counter()

        try:
            result = await self._llm.ainvoke(
                input,
                config=config,
                **kwargs,
            )

            LLM_REQUESTS_TOTAL.labels(
                model=self._model,
                agent=self._agent,
                status="success",
            ).inc()

            self._record_tokens(result)

            return result

        except Exception:
            LLM_REQUESTS_TOTAL.labels(
                model=self._model,
                agent=self._agent,
                status="error",
            ).inc()
            raise

        finally:
            LLM_LATENCY_SECONDS.labels(
                model=self._model,
                agent=self._agent,
            ).observe(time.perf_counter() - start)

    def _record_tokens(self, result: Any) -> None:
        usage = getattr(result, "usage_metadata", None)

        if not usage:
            return

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)

        if input_tokens:
            LLM_TOKENS_TOTAL.labels(
                model=self._model,
                agent=self._agent,
                type="prompt",
            ).inc(input_tokens)

        if output_tokens:
            LLM_TOKENS_TOTAL.labels(
                model=self._model,
                agent=self._agent,
                type="completion",
            ).inc(output_tokens)

        if total_tokens:
            LLM_TOKENS_TOTAL.labels(
                model=self._model,
                agent=self._agent,
                type="total",
            ).inc(total_tokens)

