import os
import csv
from run_tests import run_single_turn

TOP_K_VALUES = [
    3,
    5,
    7,
    10,
]

results = []

for top_k in TOP_K_VALUES:
    os.environ["RAG_TOP_K"] = str(top_k)

    passed, total = run_single_turn()

    results.append(
        {
            "top_k": top_k,
            "passed": passed,
            "total": total,
        }
    )

with open("tests/results/top_k_results.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "top_k",
            "passed",
            "total",
        ],
    )

    writer.writeheader()

    for row in results:
        writer.writerow(row)
