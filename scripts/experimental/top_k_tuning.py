from __future__ import annotations

import csv
import os
import time
from pathlib import Path

from scripts.experimental.e2e_chat import (
    ChatClient,
    E2ERunStats,
    run_single_turn,
)


TOP_K_VALUES = [3, 5, 7, 10]

RESULTS_DIR = Path("tests/results")
RESULTS_FILE = RESULTS_DIR / "top_k_results.csv"


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    client = ChatClient()

    print("=" * 60)
    print("RAG TOP-K TUNING")
    print("=" * 60)

    print("\nChecking application availability...")
    try:
        client.health_check()
    except Exception as exc:
        print(f"❌ Application is not available: {exc}")
        return 1

    print("✅ Application is healthy")

    results: list[dict[str, object]] = []

    for top_k in TOP_K_VALUES:
        print("\n" + "=" * 60)
        print(f"Testing RAG_TOP_K={top_k}")
        print("=" * 60)

        os.environ["RAG_TOP_K"] = str(top_k)

        stats = E2ERunStats(
            started_at=time.monotonic(),
        )

        result = run_single_turn(
            client,
            stats,
        )

        results.append(
            {
                "top_k": top_k,
                "passed": result.passed,
                "total": result.total,
                "success_rate": round(result.percentage, 2),
                "duration_seconds": round(result.duration, 2),
                "requests": stats.requests_total,
                "tokens": stats.tokens_total,
                "average_tokens": round(stats.average_tokens, 2),
            }
        )

    with RESULTS_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "top_k",
                "passed",
                "total",
                "success_rate",
                "duration_seconds",
                "requests",
                "tokens",
                "average_tokens",
            ],
        )

        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 60)
    print("TOP-K TUNING RESULTS")
    print("=" * 60)

    for row in results:
        print(
            f"top_k={row['top_k']:>2}  "
            f"{row['passed']}/{row['total']}  "
            f"{row['success_rate']:.2f}%"
        )

    print(f"\nResults saved to: {RESULTS_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

