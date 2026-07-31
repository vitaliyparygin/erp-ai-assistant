import os
import csv
from run_tests import run_single_turn

THRESHOLDS = [
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
]

results = []

for threshold in THRESHOLDS:
    os.environ["RAG_SCORE_THRESHOLD"] = str(threshold)

    passed, total = run_single_turn()

    results.append(
        {
            "threshold": threshold,
            "passed": passed,
            "total": total,
        }
    )

with open("tests/results/threshold_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "threshold",
            "passed",
            "total",
        ],
    )

    writer.writeheader()

    for row in results:
        writer.writerow(row)
