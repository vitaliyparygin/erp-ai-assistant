# Configuration Guide

## `benchmark.yaml`

```yaml
dataset: tests/datasets
output: benchmarks
template: erp
reader: pdfplumber
question_generator: template
language: en
max_questions_per_document: 6
recursive: true
```

| Key | Type | Default | Meaning |
|---|---|---|---|
| `dataset` | path | `tests/datasets` | Directory scanned for documents |
| `output` | path | `benchmarks` | Directory all artifacts are written to |
| `template` | string | `generic` | Built-in name, `.py` file path, or dotted module path (see Plugin Guide) |
| `reader` | string | `pdfplumber` | Reserved for future reader-selection support; readers are currently chosen automatically by file extension |
| `question_generator` | string | `template` | Reserved for future CLI-level generator selection (`template` or `llm`); select programmatically today via `BenchmarkPipeline(generator=...)` |
| `language` | string | `en` | Reserved for future localized question phrasing |
| `max_questions_per_document` | int (1–100) | `6` | Upper bound on generated questions per document |
| `recursive` | bool | `true` | Whether the scanner walks subdirectories |

Load it explicitly or let the CLI find it via `--config`:

```python
from rag_benchmark.config import BenchmarkConfig
config = BenchmarkConfig.load("benchmark.yaml")
```

## CLI flag precedence

For every command, configuration is resolved as:

```
BenchmarkConfig defaults  →  values from --config file  →  explicit CLI flags
```

i.e. an explicit `--dataset ./other-docs` always wins over whatever the
YAML file says, but flags you don't pass never overwrite what the YAML
file specified.

## Common flags

| Flag | Applies to | Effect |
|---|---|---|
| `--dataset PATH` | `scan`, `generate`, `report`, `export` | Override the dataset directory |
| `--output PATH` | all commands | Override the output directory |
| `--template NAME_OR_PATH` | `generate`, `report`, `export`, `init` | Override the template |
| `--config PATH` | all commands | Path to `benchmark.yaml` |
| `--force` | `init`, `generate`, `report`, `export` | Overwrite existing output files instead of failing |
| `--verbose` | all commands | INFO-level logging |
| `--dry-run` | `generate`, `report`, `export` | Compute everything but write nothing; prints what would be written |

## Per-project config example

A per-domain project typically keeps its own `benchmark.yaml` at its
repo root, pointing at its own dataset and template plugin, while
depending on `rag-benchmark` as a regular package:

```yaml
# ai-erp-assistant/benchmark.yaml
dataset: eval/documents
output: eval/benchmarks
template: eval/erp_template.py
max_questions_per_document: 8
```

```bash
cd ai-erp-assistant
rag-benchmark export --config benchmark.yaml
```

No changes to `rag_benchmark`'s source are required for this to work.
