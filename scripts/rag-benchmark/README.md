# rag-benchmark

Framework-agnostic benchmark dataset and evaluation asset generator for
Retrieval-Augmented Generation (RAG) systems.

`rag-benchmark` scans a directory of documents, classifies them, extracts
metadata, and generates realistic benchmark questions — producing a
`benchmark_queries.json`, evaluation CSV scaffolds, and a Markdown report.
It contains **no domain-specific logic**: everything about a domain (ERP,
medical, legal, HR, documentation, support, ...) lives in a **template
plugin**, so the same package works across every RAG project you own.

```
Documents  ─▶  Scan  ─▶  Classify  ─▶  Extract Metadata  ─▶  Generate Questions  ─▶  Export
```

## Install

```bash
pip install -e .
# or, with LLM-based question generation and dev tooling:
pip install -e ".[llm,dev]"
```

## Quick start

```bash
# Scaffold a config + folders
rag-benchmark init --output my-benchmark --template erp

# Drop your documents into my-benchmark/datasets/, then:
rag-benchmark scan     --config my-benchmark/benchmark.yaml
rag-benchmark generate --config my-benchmark/benchmark.yaml
rag-benchmark report   --config my-benchmark/benchmark.yaml
rag-benchmark validate --config my-benchmark/benchmark.yaml
rag-benchmark export   --config my-benchmark/benchmark.yaml
```

`export` runs the whole pipeline and writes every artifact in one shot:

```
my-benchmark/benchmarks/
├── benchmark_queries.json
├── retrieval_metrics.csv      # scaffold, ready for evaluation-run results
├── latency_metrics.csv        # scaffold, ready for evaluation-run results
└── benchmark_results_latest.md
```

## CLI reference

| Command | Purpose |
|---|---|
| `init` | Scaffold `benchmark.yaml` plus `datasets/` and `benchmarks/` directories |
| `scan` | List documents discovered in the dataset directory |
| `generate` | Run the pipeline and write `benchmark_queries.json` |
| `report` | Run the pipeline and write `benchmark_results_latest.md` |
| `validate` | Check an existing `benchmark_queries.json` for structural issues |
| `export` | Run the pipeline and write JSON + CSV + Markdown together |

Common flags: `--dataset`, `--output`, `--template`, `--config`, `--force`,
`--verbose`, `--dry-run`.

## Using it as a library

```python
from rag_benchmark import BenchmarkConfig, BenchmarkPipeline

config = BenchmarkConfig.load("benchmark.yaml")
pipeline = BenchmarkPipeline()
classified_documents, dataset = pipeline.run(config)

for query in dataset.queries:
    print(query.query, "->", query.expected_document)
```

Because `rag_benchmark` is a normal installable package, an existing RAG
project (e.g. an AI ERP Assistant) can depend on it in `pyproject.toml`
and reuse it without touching this package's source — it only needs to
point `--template` at its own plugin.

## Documentation

- [Architecture](docs/architecture.md) — how the pipeline is composed and why
- [Plugin Guide](docs/plugin-guide.md) — how to write a custom template
- [Configuration Guide](docs/configuration-guide.md) — `benchmark.yaml` reference
- [Developer Guide](docs/developer-guide.md) — running tests, linting, typing

## Bundled templates

`generic`, `erp`, `medical`, `legal` — see `src/rag_benchmark/templates/`.
Each is a plain Python module with no dependency on the rest of the
package's internals beyond the public `ClassificationRule`, `FieldRule`,
and `QuestionSpec` data contracts, so a new domain template can be written
by copying one of these files.

## License

MIT — see [LICENSE](LICENSE).
