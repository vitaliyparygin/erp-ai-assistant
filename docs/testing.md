# Testing

The project uses Pytest.

## Run all tests

```bash
pytest
```

## Run benchmark tests

```bash
pytest scripts/rag-benchmark/tests
```

## Run a single test

```bash
pytest scripts/rag-benchmark/tests/test_cli.py
```

## Run with coverage

```bash
pytest --cov=app --cov=scripts/rag-benchmark
```

## Benchmark validation

Generate benchmark data

```bash
rag-benchmark generate
```

Validate

```bash
rag-benchmark validate
```

Generate report

```bash
rag-benchmark report
```

Export all artifacts

```bash
rag-benchmark export
```

## Continuous Integration

Before opening a Pull Request, verify that:

- all tests pass
- benchmark generation succeeds
- benchmark validation succeeds
- lint passes
- formatting passes

Recommended commands

```bash
pytest

ruff check .

black --check .
```