"""
End-to-end acceptance runner for the AI ERP Assistant.

Unlike the pytest suite, this script sends real HTTP requests to a running
FastAPI application and validates complete chat scenarios through the
application stack.

Run:
    python scripts/e2e_chat.py

Requirements:
    - FastAPI application must be running on BASE_URL.
    - Required infrastructure (PostgreSQL, Redis, Qdrant, Ollama, etc.)
      must be available.
    - Test datasets must exist under tests/data/.
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 120

DATA_DIR = Path(__file__).resolve().parent.parent / "tests" / "data"

NOT_FOUND_PATTERNS = (
    "не зазнач",
    "не вказано",
    "не знайден",
    "відсут",
    "не містить",
    "not provided",
    "not found",
    "does not contain",
    "not available",
    "is not provided",
    "не приведений",
    "немає",
    "не заповнений",
)


# =============================================================================
# Statistics
# =============================================================================


@dataclass
class ScenarioResult:
    name: str
    passed: int
    total: int
    duration: float

    @property
    def percentage(self) -> float:
        if self.total == 0:
            return 100.0
        return self.passed / self.total * 100

    @property
    def failed(self) -> int:
        return self.total - self.passed


@dataclass
class E2ERunStats:
    started_at: float
    tokens_total: int = 0
    requests_total: int = 0
    scenarios: list[ScenarioResult] | None = None

    def __post_init__(self) -> None:
        if self.scenarios is None:
            self.scenarios = []

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started_at

    @property
    def total_passed(self) -> int:
        return sum(result.passed for result in self.scenarios)

    @property
    def total_tests(self) -> int:
        return sum(result.total for result in self.scenarios)

    @property
    def total_failed(self) -> int:
        return self.total_tests - self.total_passed

    @property
    def success_rate(self) -> float:
        if self.total_tests == 0:
            return 100.0
        return self.total_passed / self.total_tests * 100

    @property
    def average_tokens(self) -> float:
        if self.requests_total == 0:
            return 0.0
        return self.tokens_total / self.requests_total


# =============================================================================
# HTTP client
# =============================================================================


class ChatClient:
    """Small HTTP client used by the E2E scenarios."""

    def __init__(
        self,
        base_url: str = BASE_URL,
        timeout: int = REQUEST_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health_check(self) -> None:
        """Fail fast if the application is not available."""
        response = requests.get(
            f"{self.base_url}/health",
            timeout=10,
        )
        response.raise_for_status()

    def ask(
        self,
        question: str,
        *,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Send one chat request and validate the response contract."""
        payload: dict[str, Any] = {
            "message": question,
        }

        if session_id is not None:
            payload["session_id"] = session_id

        response = requests.post(
            f"{self.base_url}/api/v1/chat/",
            json=payload,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            print(
                f"\nHTTP {response.status_code} for question:\n"
                f"  {question}\n"
                f"Response: {response.text}\n"
            )

        response.raise_for_status()

        data = response.json()

        required_fields = (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "latency_ms",
            "agent_trace",
            "answer",
            "citations",
        )

        missing = [field for field in required_fields if field not in data]

        if missing:
            raise AssertionError(f"Chat response is missing fields: {missing}")

        return data


# =============================================================================
# Helpers
# =============================================================================


def load_json(filename: str) -> Any:
    """Load an E2E dataset from tests/data."""
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"E2E dataset not found: {path}")

    with path.open(encoding="utf-8") as file:
        return json.load(file)


def record_response(
    stats: E2ERunStats,
    response: dict[str, Any],
) -> None:
    """Update global request/token statistics."""
    stats.requests_total += 1
    stats.input_tokens += int(response.get("input_tokens", 0) or 0)
    stats.output_tokens += int(response.get("output_tokens", 0) or 0)
    stats.total_tokens += int(response.get("total_tokens", 0) or 0)


def expected_answer_matches(
    answer: str,
    expected: list[str],
) -> bool:
    """Return True when at least one expected fragment is present."""
    answer_lower = answer.lower()

    return any(expected_value.lower() in answer_lower for expected_value in expected)


def print_result(
    question: str,
    passed: bool,
    details: str = "",
) -> None:
    """Print one compact scenario result."""
    if passed:
        print(f"  ✅ {question}")
    else:
        suffix = f" — {details}" if details else ""
        print(f"  ❌ {question}{suffix}")


# =============================================================================
# Scenarios
# =============================================================================


def run_single_turn(
    client: ChatClient,
    stats: E2ERunStats,
) -> ScenarioResult:
    """Run independent single-turn QA scenarios."""
    print("\n=== Single-turn QA ===")

    started = time.monotonic()
    tests = load_json("single_turn.json")

    passed = 0

    for test in tests:
        question = test["question"]

        try:
            response = client.ask(question)
            record_response(stats, response)

            answer = response["answer"]
            ok = expected_answer_matches(
                answer,
                test["expected"],
            )

            if ok:
                passed += 1
            else:
                print_result(
                    question,
                    False,
                    f"answer={answer!r}",
                )

        except Exception as exc:
            print_result(
                question,
                False,
                f"error={exc}",
            )

    result = ScenarioResult(
        name="Single-turn QA",
        passed=passed,
        total=len(tests),
        duration=time.monotonic() - started,
    )

    print(f"  Result: {result.passed}/{result.total} " f"({result.percentage:.1f}%)")

    return result


def run_citations(
    client: ChatClient,
    stats: E2ERunStats,
) -> ScenarioResult:
    """Validate that the top citation points to the expected document."""
    print("\n=== Citation accuracy ===")

    started = time.monotonic()
    tests = load_json("citations.json")

    passed = 0

    for test in tests:
        question = test["question"]

        try:
            response = client.ask(question)
            record_response(stats, response)

            citations = response.get("citations", [])

            top_document = citations[0].get("document_name", "") if citations else ""

            expected_documents = test["expected_doc"]

            if isinstance(expected_documents, str):
                expected_documents = [expected_documents]

            ok = top_document in expected_documents

            if ok:
                passed += 1
            else:
                print_result(
                    question,
                    False,
                    (f"expected={expected_documents}, " f"actual={top_document!r}"),
                )

        except Exception as exc:
            print_result(
                question,
                False,
                f"error={exc}",
            )

    result = ScenarioResult(
        name="Citation accuracy",
        passed=passed,
        total=len(tests),
        duration=time.monotonic() - started,
    )

    print(f"  Result: {result.passed}/{result.total} " f"({result.percentage:.1f}%)")

    return result


def run_multi_turn(
    client: ChatClient,
    stats: E2ERunStats,
) -> ScenarioResult:
    """Run multi-turn conversations using a persistent session ID."""
    print("\n=== Multi-turn conversation ===")

    started = time.monotonic()
    conversations = load_json("multi_turn.json")

    passed = 0
    total = 0

    for conversation in conversations:
        session_id = str(uuid.uuid4())

        print(f"\n  Conversation: {conversation['name']}")

        for step in conversation["steps"]:
            question = step["question"]
            total += 1

            try:
                response = client.ask(
                    question,
                    session_id=session_id,
                )
                record_response(stats, response)

                answer = response["answer"]

                ok = expected_answer_matches(
                    answer,
                    step["expected"],
                )

                if ok:
                    passed += 1
                else:
                    print_result(
                        question,
                        False,
                        f"answer={answer!r}",
                    )

            except Exception as exc:
                print_result(
                    question,
                    False,
                    f"error={exc}",
                )

    result = ScenarioResult(
        name="Multi-turn conversation",
        passed=passed,
        total=total,
        duration=time.monotonic() - started,
    )

    print(f"\n  Result: {result.passed}/{result.total} " f"({result.percentage:.1f}%)")

    return result


def run_not_found(
    client: ChatClient,
    stats: E2ERunStats,
) -> ScenarioResult:
    """Validate answers for questions where information is absent."""
    print("\n=== Missing-information handling ===")

    started = time.monotonic()
    tests = load_json("not_found.json")

    passed = 0

    for test in tests:
        question = test["question"]

        try:
            response = client.ask(question)
            record_response(stats, response)

            answer = response["answer"].lower()

            ok = any(pattern in answer for pattern in NOT_FOUND_PATTERNS)

            if ok:
                passed += 1
            else:
                print_result(
                    question,
                    False,
                    f"answer={response['answer']!r}",
                )

        except Exception as exc:
            print_result(
                question,
                False,
                f"error={exc}",
            )

    result = ScenarioResult(
        name="Missing-information handling",
        passed=passed,
        total=len(tests),
        duration=time.monotonic() - started,
    )

    print(f"  Result: {result.passed}/{result.total} " f"({result.percentage:.1f}%)")

    return result


def run_disambiguation(
    client: ChatClient,
    stats: E2ERunStats,
) -> ScenarioResult:
    """Validate ambiguous-query handling."""
    print("\n=== Query disambiguation ===")

    started = time.monotonic()
    tests = load_json("ambiguity_tests.json")

    passed = 0

    for test in tests:
        question = test["question"]

        try:
            response = client.ask(question)
            record_response(stats, response)

            answer = response["answer"].lower()
            citations = response.get("citations", [])
            agent_trace = response.get("agent_trace", {})

            asks_for_clarification = "уточніть" in answer

            has_no_citations = not citations

            disambiguation_trace = bool(agent_trace.get("disambiguation"))

            ok = asks_for_clarification or has_no_citations or disambiguation_trace

            if ok:
                passed += 1
            else:
                print_result(
                    question,
                    False,
                    f"answer={response['answer']!r}",
                )

        except Exception as exc:
            print_result(
                question,
                False,
                f"error={exc}",
            )

    result = ScenarioResult(
        name="Query disambiguation",
        passed=passed,
        total=len(tests),
        duration=time.monotonic() - started,
    )

    print(f"  Result: {result.passed}/{result.total} " f"({result.percentage:.1f}%)")

    return result


# =============================================================================
# Main
# =============================================================================


def print_summary(stats: E2ERunStats) -> None:
    """Print the final E2E report."""
    print("\n" + "=" * 60)
    print("AI ERP Assistant — E2E ACCEPTANCE REPORT")
    print("=" * 60)

    for result in stats.scenarios:
        print(
            f"{result.name:<32}"
            f"{result.passed:>4}/{result.total:<4}"
            f" {result.percentage:>6.1f}%"
            f"  {result.duration:>7.2f}s"
        )

    print("-" * 60)

    print(
        f"{'TOTAL':<32}"
        f"{stats.total_passed:>4}/{stats.total_tests:<4}"
        f" {stats.success_rate:>6.1f}%"
    )

    print()
    print(f"Requests       : {stats.requests_total}")
    print(f"Tokens         : {stats.tokens_total}")
    print(f"Average tokens : {stats.average_tokens:.1f}")
    print(f"Duration       : {stats.elapsed:.2f}s")

    print()

    if stats.total_failed == 0:
        print("STATUS         : ✅ PASSED")
    else:
        print(f"STATUS         : ❌ FAILED " f"({stats.total_failed} failed)")

    print("=" * 60)


def main() -> int:
    """Run all E2E acceptance scenarios."""
    stats = E2ERunStats(
        started_at=time.monotonic(),
    )

    client = ChatClient()

    print("=" * 60)
    print("AI ERP Assistant — E2E acceptance runner")
    print(f"Server: {client.base_url}")
    print("=" * 60)

    try:
        print("\nChecking application availability...")
        client.health_check()
        print("✅ Application is healthy")

    except requests.RequestException as exc:
        print("\n❌ Application is not available.")
        print(f"Server: {client.base_url}")
        print(f"Error: {exc}")
        print("\nStart the application before running E2E scenarios, " "for example:")
        print("  python -m uvicorn app.main:app --reload")
        return 1

    try:
        stats.scenarios.append(run_single_turn(client, stats))

        stats.scenarios.append(run_disambiguation(client, stats))

        stats.scenarios.append(run_not_found(client, stats))

        stats.scenarios.append(run_citations(client, stats))

        stats.scenarios.append(run_multi_turn(client, stats))

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        return 130

    except Exception as exc:
        print("\n❌ E2E runner failed unexpectedly:")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    finally:
        print_summary(stats)

    return 0 if stats.total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
