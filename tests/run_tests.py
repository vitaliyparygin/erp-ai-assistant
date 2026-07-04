import requests
import json
import uuid
import time
import functools

BASE_URL = "http://localhost:8000"

tokens_total = 0
runs_count = 0


def load_tests(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ask(question):
    global tokens_total, runs_count
    response = requests.post(
        f"{BASE_URL}/api/v1/chat/",
        json={"message": question},
    )

    if response.status_code != 200:
        print(response.text)

    response.raise_for_status()

    data = response.json()

    assert "tokens_used" in data
    assert "latency_ms" in data
    assert "agent_trace" in data
    assert "answer" in data
    assert "citations" in data

    tokens_total += response.json()["tokens_used"]
    runs_count += 1

    return data

def test_decor(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"=== {func.__name__} test ===")

        result = func(*args, **kwargs)

        return result

    return wrapper

@test_decor
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
        if ok:
            passed += 1

        print(
            test["question"],
            "✅" if ok else f"❌{answer} != {test['expected']}"
        )

    return passed, len(tests)


@test_decor
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
                top_doc in
                test["expected_doc"]
        )
        if ok:
            passed += 1

        print(
            test["question"],
            test["expected_doc"],
            "✅" if ok else f"❌  != {top_doc} | {ok}"
        )

    return passed, len(tests)


@test_decor
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

            total += 1
            passed += ok

            print(
                conv["name"],
                step["question"],
                "✅" if ok else f"❌ {answer} != {step['expected']}"
            )

    return passed, total

@test_decor
def run_not_found():
    tests = load_tests(
        "tests/data/not_found.json"
    )
    NOT_FOUND_PATTERNS = [
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
        "does not contain",
        "немає",
        "не зазначено",
        "не заповнений"
    ]
    passed = 0

    for test in tests:
        result = ask(test["question"])
        answer = result["answer"]
        ok = any(
            pattern in answer.lower()
            for pattern in NOT_FOUND_PATTERNS
        )

        passed += ok

        print(
            test["question"],
            "✅" if ok else f"❌ {answer}",

        )

    return passed, len(tests)

@test_decor
def run_disambiguation():
    tests = load_tests(
        "tests/data/ambiguity_tests.json"
    )
    TEST_PATTERNS = [
        "уточніть",
    ]
    passed = 0

    for test in tests:
        result = ask(test["question"])
        answer = result["answer"]
        ok = any(
            pattern in answer.lower() for pattern in  TEST_PATTERNS or
            len(result["citations"]) == 0 or
            result["agent_trace"].get("disambiguation")
        )
        if ok:
            passed += ok
        print(
            test["question"],
            "✅" if ok else "❌ {answer} != {test['expected']}",

        )

    return passed, len(tests)


start_time = time.monotonic()
single_passed = single_total = citation_passed = citation_total = multi_passed =\
    multi_total = notfound_passed = notfound_total = disambiguation_passed = disambiguation_total = 0

single_passed, single_total = run_single_turn()
disambiguation_passed, disambiguation_total = run_disambiguation()
notfound_passed, notfound_total = run_not_found()
citation_passed, citation_total = run_citations()
multi_passed, multi_total = run_multi_turn()




print("=" * 50)

if single_total > 0:
    print(
        f"Single-turn : {single_passed}/{single_total}"
    )
if citation_total > 0:
    print(
        f"Citations   : {citation_passed}/{citation_total}"
    )
if multi_total > 0:
    print(
        f"Multi-turn  : {multi_passed}/{multi_total}"
    )
if notfound_total > 0:
    print(
        f"Not-found-turn  : {notfound_passed}/{notfound_total}"
    )
if disambiguation_total > 0:
    print(
        f"Not-found-turn  : {disambiguation_passed}/{disambiguation_total}"
    )
# todo add tests
# todo  mixed, regression, retrival, synonym

total_passed = (
        single_passed
        + citation_passed
        + multi_passed
        + notfound_passed
        + disambiguation_passed
)

total_tests = (
        single_total
        + citation_total
        + multi_total
        + notfound_total
        + disambiguation_passed
)
latency_ms = round((time.monotonic() - start_time), 2)
print("-" * 50)
print("tokens_total =", tokens_total)
print("runs_count =", runs_count)
avg_tokens = tokens_total / runs_count
print(
    f"TOTAL       : {total_passed}/{total_tests}"
)
print()
print(
    f"Tokens total / runs_count = avg_tokens      : {tokens_total} / {runs_count} = {avg_tokens}"
)
print(
    f"Latency       : {latency_ms}'s"
)

