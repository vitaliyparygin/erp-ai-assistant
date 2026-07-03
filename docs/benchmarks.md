# Benchmark

This document describes how the AI ERP Assistant performance is measured and monitored.

---

# Objective

The benchmark suite evaluates:

- Retrieval quality
- Response latency
- LLM performance
- Reranking efficiency
- End-to-end response time

---

# Test Environment

| Component | Value |
|-----------|-------|
| OS | macOS |
| Python | 3.12 |
| FastAPI | Latest |
| Ollama | Local |
| LLM | Qwen2.5:7B |
| Vector Database | Qdrant |
| Embedding Model | bge-small-en-v1.5 *(or current model)* |
| Dataset | ERP sample documents |

---

# Dataset

Current benchmark dataset contains documents from several ERP domains:

- Contracts
- Purchase Orders
- Vendor Profiles
- CRM
- HR
- Accounting
- Service Management
- Project Management
- Utilities

Example documents:

- Purchase Order.pdf
- Vendor Profile.pdf
- Service Ticket.pdf
- ERP Master Contract.pdf
- Employment Contract.pdf

---

# Benchmark Scenarios

## Retrieval

Goal

Measure semantic search quality.

Example queries

| Query | Expected document |
|--------|-------------------|
| Find vendor phone | Vendor Profile.pdf |
| Total sum in purchase order | Purchase Order.pdf |
| Status ticket TKT-1001 | Service Ticket.pdf |
| Show project status | PROJECT STATUS REPORT.pdf |

Metrics

- Recall@K
- Precision@K
- Average similarity score

---

## Reranking

Goal

Evaluate CrossEncoder improvements.

Metrics

- Top-1 accuracy
- MRR
- NDCG

Compare

| Before | After |
|----------|---------|
| Vector Search | CrossEncoder |

---

## Summarization

Goal

Measure answer quality.

Metrics

- Answer correctness
- Hallucination rate
- Citation coverage

---

## End-to-End

Goal

Measure total response time.

Metrics

- Retrieval latency
- LLM latency
- Citation latency
- Total latency

---

# Sample Results

| Query | Latency (ms) | Tokens | Sources |
|--------|-------------:|-------:|--------:|
| Vendor phone | 3668 | 535 | 3 |
| Purchase Order | 3940 | 656 | 3 |
| Service Ticket | 2892 | 470 | 1 |

---

# Agent Metrics

| Agent | Metric |
|---------|--------|
| Memory | Load time |
| Retriever | Search latency |
| Research | Processing latency |
| Summarizer | Generation latency |
| Citation | Citation generation |

---

# Future Benchmarks

Planned improvements:

- Hybrid Search
- CrossEncoder reranking
- Metadata filtering
- Streaming responses
- Multi-turn conversations

---

# Benchmark Commands

Run benchmark suite

```bash
pytest tests/benchmark/
```

Measure API latency

```bash
time curl -X POST http://localhost:8000/api/v1/chat \
-H "Content-Type: application/json" \
-d '{"message":"Find vendor phone"}'
```

Future:

```bash
make benchmark
```

---

# Notes

Benchmark results depend on:

- hardware
- selected LLM
- embedding model
- dataset size
- number of indexed documents

Results should be compared only under similar conditions.