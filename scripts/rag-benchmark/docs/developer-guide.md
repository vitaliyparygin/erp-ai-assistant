# Developer Guide

## Setup

```bash
git clone <repo>
cd rag-benchmark
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,llm]"
```

## Project layout

```
src/rag_benchmark/
├── cli.py                 Typer CLI entry point
├── config.py               BenchmarkConfig (YAML-backed)
├── models.py                All shared Pydantic data models
├── scanner.py               Filesystem discovery
├── pdf_reader.py            DocumentReader ABC + PDF/DOCX/TXT/MD readers
├── classifier.py            DocumentClassifier ABC + DefaultClassifier
├── extractor.py             MetadataExtractor ABC + RegexMetadataExtractor
├── generators/               QuestionGenerator ABC + template/LLM implementations
├── templates/                Template plugin contract + generic/erp/medical/legal
├── writers/                  JSON/CSV/Markdown output writers
├── metrics.py                Statistics + validation
├── pipeline.py                Orchestrates the full run
└── utils.py                   Logging, ids, text helpers
```

## Running tests

```bash
pytest
pytest --cov=rag_benchmark --cov-report=term-missing
```

Tests are organized to mirror the source layout: `test_scanner.py`,
`test_classifier.py`, `test_extractor.py`, `test_generator.py`,
`test_writers.py`, `test_metrics.py`, `test_cli.py`. `conftest.py`
provides a `dataset_dir` fixture with representative sample documents
(invoice, vendor profile, an unclassifiable markdown note, and an
unsupported file to confirm the scanner skips it).

CLI tests use `typer.testing.CliRunner` and exercise every command
end-to-end against `tmp_path` fixtures — no network or external services
are required.

## Linting, formatting, typing

```bash
black src tests
ruff check src tests
mypy src
```

`pyproject.toml` configures all three; `mypy` runs in `strict` mode with
`disallow_untyped_defs = true`, matching the "100% type hints" requirement.

## Adding a new document format

1. Implement `DocumentReader` in `pdf_reader.py` (or a new module).
2. Add the extension to `scanner._EXTENSION_MAP` and a new
   `DocumentFormat` enum member in `models.py`.
3. Register the reader in `ReaderRegistry.__init__`.
4. Add a fixture file and a scanner/reader test.

## Adding a new writer/report format

Add a function to `writers/`, export it from `writers/__init__.py`, and
wire a new CLI flag/command in `cli.py` if it should be user-facing.

## Release checklist

- [ ] `pytest` passes
- [ ] `ruff check` and `mypy` are clean
- [ ] `README.md` and `docs/` reflect any new CLI flags or config keys
- [ ] Version bumped in `pyproject.toml` and `rag_benchmark.__version__`
