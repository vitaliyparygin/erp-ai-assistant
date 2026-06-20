import csv
import requests
import yaml
import json
import uuid

API_URL = "http://localhost:8000"

def load_tests(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def ask(question: str, session_id: str | None = None, ):
    payload = {
        "message": question
    }

    if session_id:
        payload["session_id"] = session_id

    response = requests.post(
        f"{API_URL}/api/v1/chat/",
        json=payload,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()

def run_single_turn():
    tests = load_tests(
        "tests/data/single_turn.json"
    )

    passed = 0

    for test in tests:
        result = ask(test["question"])
        answer = result["answer"]

        ok = any(
            expected.lower() in answer.lower()
            for expected in test["expected"]
        )
        print(f"{answer} = {test['expected']} | {ok}")
        passed += ok

        print(
            test["question"],
            "✅" if ok else "❌"
        )

    return passed, len(tests)


def run_citations():
    tests = load_tests(
        "tests/data/citations.json"
    )

    passed = 0

    for test in tests:
        result = ask(
            test["question"]
        )

        citations = result.get(
            "citations",
            []
        )

        top_doc = (
            citations[0]["document_name"]
            if citations
            else ""
        )


        ok = (
                top_doc ==
                test["expected_doc"]
        )
        print(f"{top_doc} = {test['expected_doc']} | {ok}")
        passed += ok

        print(
            test["question"],
            top_doc,
            "✅" if ok else "❌"
        )

    return passed, len(tests)


def run_multi_turn():
    conversations = load_tests(
        "tests/data/multi_turn.json"
    )

    passed = 0
    total = 0

    for conv in conversations:

        session_id = str(
            uuid.uuid4()
        )

        for step in conv["steps"]:
            result = ask(
                step["question"],
                session_id=session_id
            )

            answer = result["answer"]

            ok = any(
                expected.lower() in answer.lower()
                for expected in step["expected"]
            )
            print(f"{answer} = {step['expected']} | {ok}")
            total += 1
            passed += ok

            print(
                conv["name"],
                step["question"],
                "✅" if ok else "❌"
            )

    return passed, total


single_passed, single_total = run_single_turn()

citation_passed, citation_total = run_citations()

multi_passed, multi_total = run_multi_turn()

print()
print("=" * 50)

print(
    f"Single-turn : {single_passed}/{single_total}"
)

print(
    f"Citations   : {citation_passed}/{citation_total}"
)

print(
    f"Multi-turn  : {multi_passed}/{multi_total}"
)

total_passed = (
        single_passed
        + citation_passed
        + multi_passed
)

total_tests = (
        single_total
        + citation_total
        + multi_total
)

print("-" * 50)

print(
    f"TOTAL       : {total_passed}/{total_tests}"
)

# with open("tests/test_cases.yaml") as f:
#     config = yaml.safe_load(f)
#
# results = []
#
# for test in config["tests"]:
#
#     response = requests.post(
#         API_URL,
#         json={
#             "message": test["question"]
#         }
#     )
#
#     data = response.json()
#
#     answer = data.get("answer", "")
#
#     if "expected" in test:
#         passed = all(
#             e.lower() in answer.lower()
#             for e in test["expected"]
#         )
#
#         expected_text = "; ".join(test["expected"])
#
#     elif "expected_any" in test:
#         passed = any(
#             e.lower() in answer.lower()
#             for e in test["expected_any"]
#         )
#
#         expected_text = "; ".join(test["expected_any"])
#
#     else:
#         raise ValueError(
#             f"Test {test['question']} has no expected field"
#         )
#
#     results.append({
#         "question": test["question"],
#         "expected": expected_text,
#         "answer": answer,
#         "passed": passed,
#     })
#
# with open("tests/report.csv", "w", newline="") as f:
#     writer = csv.DictWriter(
#         f,
#         fieldnames=[
#             "question",
#             "expected",
#             "answer",
#             "passed",
#         ]
#     )
#
#     writer.writeheader()
#
#     for row in results:
#         writer.writerow(row)
#
# passed = sum(r["passed"] for r in results)
#
# print(
#     f"\nPassed {passed}/{len(results)} tests"
# )
