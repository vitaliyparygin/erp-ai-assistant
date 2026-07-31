from __future__ import annotations

import csv
import json
import statistics
import time
from datetime import date
from pathlib import Path

import requests

API_URL = "http://localhost:8000/api/v1/chat"

ROOT = Path(__file__).resolve().parent.parent

BENCHMARK_DIR = ROOT / "benchmarks"

QUERIES_FILE = BENCHMARK_DIR / "benchmark_queries.json"

LATENCY_CSV = BENCHMARK_DIR / "latency_metrics.csv"

RETRIEVAL_CSV = BENCHMARK_DIR / "retrieval_metrics.csv"

LATEST_MD = BENCHMARK_DIR / "benchmark_results_latest.md"


today = date.today().isoformat()

HISTORY_MD = BENCHMARK_DIR / "history" / f"benchmark_{today}.md"


BENCHMARK_DIR.mkdir(exist_ok=True)

(BENCHMARK_DIR / "history").mkdir(exist_ok=True)


DEFAULT_QUERIES = [
    {
        "id": 1,
        "query": "find vendor phone",
        "expected_document": "Vendor Profile.pdf",
    },
    {
        "id": 2,
        "query": "status ticket TKT-1001",
        "expected_document": "Service Ticket.pdf",
    },
    {
        "id": 3,
        "query": "total sum in purchase order PO-2024-001",
        "expected_document": "Purchase Order.pdf",
    },
    {
        "id": 4,
        "query": "show project status",
        "expected_document": "PROJECT STATUS REPORT.pdf",
    },
    {
        "id": 5,
        "query": "who is contractor",
        "expected_document": "erp_master_contract.pdf",
    },
]

if not QUERIES_FILE.exists():
    QUERIES_FILE.write_text(
        json.dumps(DEFAULT_QUERIES, indent=2),
        encoding="utf-8",
    )
    print(f"Created default benchmark file: {QUERIES_FILE}")

with QUERIES_FILE.open("r", encoding="utf-8") as f:
    queries = json.load(f)

latencies = []

rows = []

for item in queries:
    payload = {"message": item["query"]}

    start = time.perf_counter()

    response = requests.post(API_URL, json=payload)

    elapsed = (time.perf_counter() - start) * 1000

    data = response.json()

    citations = data.get("citations", [])

    top_document = ""

    if citations:
        top_document = citations[0]["document_name"]

    success = top_document == item["expected_document"]

    rows.append(
        {
            "query": item["query"],
            "expected": item["expected_document"],
            "returned": top_document,
            "success": success,
            "latency": round(elapsed, 2),
            "tokens": data.get("tokens_used", 0),
            "sources": len(citations),
        }
    )

    latencies.append(elapsed)

with open(LATENCY_CSV, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "query",
            "latency",
            "tokens",
            "sources",
        ],
    )

    writer.writeheader()

    for row in rows:
        writer.writerow(
            {
                "query": row["query"],
                "latency": row["latency"],
                "tokens": row["tokens"],
                "sources": row["sources"],
            }
        )

with open(RETRIEVAL_CSV, "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "query",
            "expected",
            "returned",
            "success",
        ],
    )

    writer.writeheader()

    for row in rows:
        writer.writerow(
            {
                "query": row["query"],
                "expected": row["expected"],
                "returned": row["returned"],
                "success": row["success"],
            }
        )

accuracy = sum(r["success"] for r in rows) / len(rows) * 100

avg_latency = statistics.mean(latencies)

report = f"""
# Benchmark Results

Date: {today}

## Summary

| Metric | Value |
|---------|------:|
| Queries | {len(rows)} |
| Accuracy | {accuracy:.1f}% |
| Average Latency | {avg_latency:.2f} ms |

---

## Results

| Query | Returned | Latency |
|--------|----------|---------|
"""

for r in rows:
    report += f"| {r['query']} | {r['returned']} | {r['latency']} ms |\n"

LATEST_MD.write_text(report)

HISTORY_MD.write_text(report)

print("Benchmark completed.")
