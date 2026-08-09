from types import SimpleNamespace
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from app.observability.llm import InstrumentedLLM


@pytest.fixture
def wrapped_llm():
    llm = MagicMock()
    return llm


def test_invoke_success(wrapped_llm):
    result = SimpleNamespace(
        content="answer",
    )
    wrapped_llm.invoke.return_value = result

    instrumented = InstrumentedLLM(
        wrapped_llm,
        model="test-model",
        agent="test-agent",
    )

    with (
        patch("app.observability.llm.LLM_REQUESTS_TOTAL.labels") as requests_labels,
        patch("app.observability.llm.LLM_LATENCY_SECONDS.labels") as latency_labels,
        patch("app.observability.llm.InstrumentedLLM._record_tokens") as record_tokens,
    ):
        result = instrumented.invoke(
            {"query": "hello"},
            config={"test": True},
        )

    assert result.content == "answer"

    wrapped_llm.invoke.assert_called_once_with(
        {"query": "hello"},
        config={"test": True},
    )

    requests_labels.assert_called_once_with(
        model="test-model",
        agent="test-agent",
        status="success",
    )
    requests_labels.return_value.inc.assert_called_once_with()

    latency_labels.assert_called_once_with(
        model="test-model",
        agent="test-agent",
    )
    latency_labels.return_value.observe.assert_called_once()

    record_tokens.assert_called_once_with(result)


def test_invoke_error_reraises_and_records_error(wrapped_llm):
    wrapped_llm.invoke.side_effect = RuntimeError("llm failed")

    instrumented = InstrumentedLLM(
        wrapped_llm,
        model="test-model",
        agent="test-agent",
    )

    with (
        patch("app.observability.llm.LLM_REQUESTS_TOTAL.labels") as requests_labels,
        patch("app.observability.llm.LLM_LATENCY_SECONDS.labels") as latency_labels,
    ):
        with pytest.raises(RuntimeError, match="llm failed"):
            instrumented.invoke("hello")

    requests_labels.assert_called_once_with(
        model="test-model",
        agent="test-agent",
        status="error",
    )
    requests_labels.return_value.inc.assert_called_once_with()

    latency_labels.assert_called_once_with(
        model="test-model",
        agent="test-agent",
    )
    latency_labels.return_value.observe.assert_called_once()


@pytest.mark.asyncio
async def test_ainvoke_success():
    llm = AsyncMock()
    result = SimpleNamespace(
        content="async answer",
    )
    llm.ainvoke.return_value = result

    instrumented = InstrumentedLLM(
        llm,
        model="test-model",
        agent="research",
    )

    with (
        patch("app.observability.llm.LLM_REQUESTS_TOTAL.labels") as requests_labels,
        patch("app.observability.llm.LLM_LATENCY_SECONDS.labels") as latency_labels,
        patch("app.observability.llm.InstrumentedLLM._record_tokens") as record_tokens,
    ):
        result = await instrumented.ainvoke(
            {"query": "hello"},
            config={"stream": False},
        )

    assert result.content == "async answer"

    llm.ainvoke.assert_awaited_once_with(
        {"query": "hello"},
        config={"stream": False},
    )

    requests_labels.assert_called_once_with(
        model="test-model",
        agent="research",
        status="success",
    )
    requests_labels.return_value.inc.assert_called_once_with()

    latency_labels.assert_called_once_with(
        model="test-model",
        agent="research",
    )
    latency_labels.return_value.observe.assert_called_once()

    record_tokens.assert_called_once_with(result)


@pytest.mark.asyncio
async def test_ainvoke_error_reraises_and_records_error():
    llm = AsyncMock()
    llm.ainvoke.side_effect = RuntimeError("ollama failed")

    instrumented = InstrumentedLLM(
        llm,
        model="test-model",
        agent="research",
    )

    with (
        patch("app.observability.llm.LLM_REQUESTS_TOTAL.labels") as requests_labels,
        patch("app.observability.llm.LLM_LATENCY_SECONDS.labels") as latency_labels,
    ):
        with pytest.raises(RuntimeError, match="ollama failed"):
            await instrumented.ainvoke("hello")

    requests_labels.assert_called_once_with(
        model="test-model",
        agent="research",
        status="error",
    )
    requests_labels.return_value.inc.assert_called_once_with()

    latency_labels.assert_called_once_with(
        model="test-model",
        agent="research",
    )
    latency_labels.return_value.observe.assert_called_once()


def test_record_tokens_without_usage_metadata():
    llm = MagicMock()

    instrumented = InstrumentedLLM(
        llm,
        model="test-model",
        agent="test-agent",
    )

    result = SimpleNamespace(content="answer")

    with patch("app.observability.llm.LLM_TOKENS_TOTAL.labels") as tokens_labels:
        instrumented._record_tokens(result)

    tokens_labels.assert_not_called()


def test_record_tokens_all_values():
    llm = MagicMock()

    instrumented = InstrumentedLLM(
        llm,
        model="test-model",
        agent="test-agent",
    )

    result = SimpleNamespace(
        usage_metadata={
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
        }
    )

    with patch("app.observability.llm.LLM_TOKENS_TOTAL.labels") as tokens_labels:
        instrumented._record_tokens(result)

    assert tokens_labels.call_count == 3

    tokens_labels.assert_any_call(
        model="test-model",
        agent="test-agent",
        type="prompt",
    )
    tokens_labels.assert_any_call(
        model="test-model",
        agent="test-agent",
        type="completion",
    )
    tokens_labels.assert_any_call(
        model="test-model",
        agent="test-agent",
        type="total",
    )

    assert tokens_labels.return_value.inc.call_count == 3


@pytest.mark.parametrize(
    "usage",
    [
        {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        {"input_tokens": 10, "output_tokens": 0, "total_tokens": 0},
        {"input_tokens": 0, "output_tokens": 20, "total_tokens": 0},
        {"input_tokens": 0, "output_tokens": 0, "total_tokens": 30},
    ],
)
def test_record_tokens_skips_zero_values(usage):
    llm = MagicMock()

    instrumented = InstrumentedLLM(
        llm,
        model="test-model",
        agent="test-agent",
    )

    result = SimpleNamespace(
        usage_metadata=usage,
    )

    with patch("app.observability.llm.LLM_TOKENS_TOTAL.labels") as tokens_labels:
        instrumented._record_tokens(result)

    expected_calls = sum(
        value > 0
        for value in (
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            usage.get("total_tokens", 0),
        )
    )

    assert tokens_labels.call_count == expected_calls
