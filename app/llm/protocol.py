from __future__ import annotations

from abc import abstractmethod
from typing import Any

from langchain_core.runnables import Runnable


class LLMProtocol(Runnable[Any, Any]):
    """Common interface for instrumented and native LLM implementations."""

    @abstractmethod
    def invoke(
        self,
        input: Any,
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke the LLM synchronously."""
        raise NotImplementedError

    @abstractmethod
    async def ainvoke(
        self,
        input: Any,
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Invoke the LLM asynchronously."""
        raise NotImplementedError
