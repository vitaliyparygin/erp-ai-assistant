import csv
import requests
import yaml

API_URL = "http://localhost:8000/api/v1/chat/"


with open("tests/test_cases.yaml") as f:
    config = yaml.safe_load(f)

results = []

for test in config["tests"]:

    response = requests.post(
        API_URL,
        json={
            "message": test["question"]
        }
    )

    data = response.json()

    answer = data.get("answer", "")

    if "expected" in test:
        passed = all(
            e.lower() in answer.lower()
            for e in test["expected"]
        )

        expected_text = "; ".join(test["expected"])

    elif "expected_any" in test:
        passed = any(
            e.lower() in answer.lower()
            for e in test["expected_any"]
        )

        expected_text = "; ".join(test["expected_any"])

    else:
        raise ValueError(
            f"Test {test['question']} has no expected field"
        )

    results.append({
        "question": test["question"],
        "expected": expected_text,
        "answer": answer,
        "passed": passed,
    })

with open("tests/report.csv", "w", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "question",
            "expected",
            "answer",
            "passed",
        ]
    )

    writer.writeheader()

    for row in results:
        writer.writerow(row)

passed = sum(r["passed"] for r in results)

print(
    f"\nPassed {passed}/{len(results)} tests"
)