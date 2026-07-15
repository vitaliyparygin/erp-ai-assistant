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

## Badges

![Python](https://img.shields.io/badge/python-3.10%2B-blue)

![License](https://img.shields.io/badge/license-MIT-green)

![CI](https://github.com/vitaliyparygin/rag-benchmark/actions/workflows/ci.yml/badge.svg)

![PyPI](https://img.shields.io/pypi/v/rag-benchmark)

![Downloads](https://img.shields.io/pypi/dm/rag-benchmark)


## Features

- Framework-agnostic RAG benchmark generation
- Template-based document classification
- Regex-based metadata extraction
- Synthetic benchmark question generation
- Dataset diagnostics and readiness analysis
- Interactive document inspection
- Extensible plugin architecture
- Rich CLI interface
- Markdown reports
- JSON benchmark export
- Easy integration into existing RAG pipelines

## Installation

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

## Commands

| Command | Description |
|----------|-------------|
| `init` | Create a new benchmark project |
| `scan` | Scan dataset and discover supported documents |
| `generate` | Generate benchmark questions |
| `diagnose` | Analyze dataset quality and readiness |
| `inspect` | Inspect a single document |
| `validate` | Validate generated benchmark dataset |
| `report` | Run the pipeline and write `benchmark_results_latest.md` |
| `export` | Run the pipeline and write JSON + CSV + Markdown together |

Common flags: `--dataset`, `--output`, `--template`, `--config`, `--force`,
`--verbose`, `--dry-run`, `--file`

## Pipeline

```
Documents
      │
      ▼
 Scan
      │
      ▼
 Read
      │
      ▼
 Classify
      │
      ▼
 Extract Metadata
      │
      ▼
 Generate Questions
      │
      ▼
 Benchmark Dataset
      │
      ▼
 Diagnostics
```

## Templates

Templates define all domain-specific behavior.

Each template contains:

- classification rules
- extraction rules
- question templates
- optional metadata

Bundled templates:

- generic
- erp
- legal
- medical

Creating a new template requires no changes to the core pipeline.

## Dataset structure

```
datasets/

    Invoice.pdf

    Purchase Order.pdf

    Contract.pdf

    Customer Card.pdf

    ...

```

Supported formats:

- PDF
- DOCX (planned)
- TXT (planned)
- Markdown (planned)

## Example output

```
benchmarks/

    benchmark_queries.json

    benchmark_results_latest.md

    retrieval_metrics.csv

    latency_metrics.csv
```

Example generated question:

```json
{
  "query": "What is the invoice number?",
  "expected_document": "Invoice.pdf",
  "expected_fields": ["invoice_number"]
}
```

## Library API

The package can also be used directly from Python.

```python
from rag_benchmark import BenchmarkConfig
from rag_benchmark import BenchmarkPipeline

config = BenchmarkConfig.load("benchmark.yaml")

pipeline = BenchmarkPipeline()

result = pipeline.execute(config)

print(result.dataset.queries)
```

The pipeline exposes reusable stages for:

- scanning
- classification
- metadata extraction
- question generation

## Architecture

The project is intentionally modular.

```
CLI

 │

 ▼

Pipeline

 ├── Scanner

 ├── Reader

 ├── Classifier

 ├── Metadata Extractor

 ├── Question Generator

 └── Diagnostics
```

Each component can be replaced independently for custom workflows.

## Examples

Example projects are available in the `examples/` directory.

```
examples/

    generic/

    erp/

    legal/
```

Each example contains:

- benchmark.yaml
- sample documents
- generated benchmark
- diagnostics report

## Contributing

Contributions are welcome.

Please:

1. Fork the repository.
2. Create a feature branch.
3. Run formatting and tests.
4. Open a Pull Request.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the complete guide.

## Roadmap

### v1.0

- Template-based benchmark generation
- Diagnostics
- Inspection
- CLI

### v1.1

- DOCX reader
- Markdown reader
- Better diagnostics
- More bundled templates

### v1.2

- LLM-based question generation
- Automatic regex suggestions
- Dataset quality scoring

### Future

- HuggingFace dataset export
- RAGAS integration
- Multi-language templates
- Web UI
- Benchmark comparison reports

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


