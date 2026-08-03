# Testing

AI ERP Assistant includes a lightweight evaluation framework for measuring retrieval quality and tuning search parameters.

Unlike traditional unit testing, the current focus is validating Retrieval-Augmented Generation (RAG) quality.

---

# Test datasets

Example datasets are stored in:

```
tests/datasets/
```

These documents are indexed into Qdrant and used during retrieval evaluation.

---

# Test cases

Queries and expected answers are defined in

```
tests/test_cases.yaml
```

Each test case contains:

- question
- expected document
- expected fields
- expected answer (optional)

---

# Running evaluation

Run the complete evaluation:

```bash
python tests/e2e_chat.py
```

Results are written to

```
tests/report.csv
```

---

# Threshold tuning

Similarity thresholds can be optimized with

```bash
python tests/threshold_tuning.py
```

The script evaluates different similarity cutoffs and reports precision / recall.

---

# Top-K tuning

Retriever Top-K can be optimized with

```bash
python tests/top_k_tuning.py
```

This helps determine the best number of retrieved chunks before reranking.

---

# Future testing roadmap

Planned testing includes:

- Unit tests
- Integration tests
- API tests
- End-to-end RAG evaluation
- Hallucination detection
- Prompt regression tests
- Multi-language evaluation
- Benchmark automation
- CI/CD integration
- Performance testing

---

# Recommended workflow

After changing:

- prompts
- retriever
- embeddings
- reranker
- chunking
- metadata extraction

run

```bash
python tests/e2e_chat.py
```

before committing changes.

---

# Continuous evaluation

Every major change to the retrieval pipeline should be evaluated against the same dataset to detect regressions in:

- Recall
- Precision
- Ranking quality
- Latency

Keeping the evaluation dataset stable allows results to be compared across versions.