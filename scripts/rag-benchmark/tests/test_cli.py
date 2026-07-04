"""Tests for rag_benchmark.cli using Typer's CliRunner."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rag_benchmark.cli import app

runner = CliRunner()


def test_init_creates_config_and_directories(tmp_path: Path) -> None:
    result = runner.invoke(app, ["init", "--output", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "benchmark.yaml").exists()
    assert (tmp_path / "datasets").is_dir()
    assert (tmp_path / "benchmarks").is_dir()


def test_init_refuses_to_overwrite_without_force(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--output", str(tmp_path)])
    result = runner.invoke(app, ["init", "--output", str(tmp_path)])
    assert result.exit_code == 1


def test_init_overwrites_with_force(tmp_path: Path) -> None:
    runner.invoke(app, ["init", "--output", str(tmp_path)])
    result = runner.invoke(app, ["init", "--output", str(tmp_path), "--force"])
    assert result.exit_code == 0


def test_scan_lists_supported_documents(dataset_dir: Path) -> None:
    result = runner.invoke(app, ["scan", "--dataset", str(dataset_dir)])
    assert result.exit_code == 0
    assert "invoice_001.txt" in result.stdout
    assert "image.png" not in result.stdout


def test_scan_missing_dataset_fails_cleanly(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scan", "--dataset", str(tmp_path / "missing")])
    assert result.exit_code == 1


def test_generate_writes_benchmark_json(dataset_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "generate",
            "--dataset", str(dataset_dir),
            "--output", str(output_dir),
            "--template", "generic",
        ],
    )
    assert result.exit_code == 0
    queries_path = output_dir / "benchmark_queries.json"
    assert queries_path.exists()
    payload = json.loads(queries_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)


def test_generate_dry_run_does_not_write_file(dataset_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "generate",
            "--dataset", str(dataset_dir),
            "--output", str(output_dir),
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert not (output_dir / "benchmark_queries.json").exists()


def test_generate_refuses_overwrite_without_force(dataset_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    args = ["generate", "--dataset", str(dataset_dir), "--output", str(output_dir)]
    first = runner.invoke(app, args)
    assert first.exit_code == 0
    second = runner.invoke(app, args)
    assert second.exit_code == 1


def test_report_writes_markdown(dataset_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    result = runner.invoke(
        app, ["report", "--dataset", str(dataset_dir), "--output", str(output_dir)]
    )
    assert result.exit_code == 0
    assert (output_dir / "benchmark_results_latest.md").exists()


def test_validate_on_clean_dataset_succeeds(dataset_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    runner.invoke(app, ["generate", "--dataset", str(dataset_dir), "--output", str(output_dir)])
    result = runner.invoke(app, ["validate", "--output", str(output_dir)])
    assert result.exit_code == 0


def test_validate_missing_file_fails(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", "--output", str(tmp_path / "nope")])
    assert result.exit_code == 1


def test_export_writes_all_artifacts(dataset_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    result = runner.invoke(
        app, ["export", "--dataset", str(dataset_dir), "--output", str(output_dir)]
    )
    assert result.exit_code == 0
    assert (output_dir / "benchmark_queries.json").exists()
    assert (output_dir / "retrieval_metrics.csv").exists()
    assert (output_dir / "latency_metrics.csv").exists()
    assert (output_dir / "benchmark_results_latest.md").exists()
