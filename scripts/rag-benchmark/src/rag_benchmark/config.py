"""Configuration model and YAML loading for rag_benchmark.

Configuration can come from (in increasing priority order):
1. Built-in defaults on BenchmarkConfig.
2. A YAML file (benchmark.yaml).
3. CLI flag overrides, applied by the caller via `BenchmarkConfig.with_overrides`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class BenchmarkConfig(BaseModel):
    """Top-level configuration for a benchmark generation run."""

    dataset: Path = Path("tests/datasets")
    output: Path = Path("benchmarks")
    template: str = "generic"
    reader: str = "pdfplumber"
    question_generator: str = "template"
    language: str = "en"
    max_questions_per_document: int = Field(default=6, ge=1, le=100)
    recursive: bool = True

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("dataset", "output", mode="before")
    @classmethod
    def _coerce_path(cls, value: str | Path) -> Path:
        return Path(value)

    @classmethod
    def load(cls, path: Path | None) -> BenchmarkConfig:
        """Load configuration from a YAML file, falling back to defaults.

        Args:
            path: Path to a YAML config file. If None or missing, defaults
                are used.

        Returns:
            A populated BenchmarkConfig instance.
        """
        if path is None or not Path(path).exists():
            return cls()
        with Path(path).open("r", encoding="utf-8") as handle:
            raw: dict[str, Any] = yaml.safe_load(handle) or {}
        return cls(**raw)

    def with_overrides(self, **overrides: Any) -> BenchmarkConfig:
        """Return a copy of this config with non-None overrides applied.

        This is meant to be fed CLI flags directly; any override that is
        None is ignored so CLI defaults never clobber a loaded config.
        """
        clean = {key: value for key, value in overrides.items() if value is not None}
        return self.model_copy(update=clean)

    def save(self, path: Path) -> None:
        """Persist this configuration to a YAML file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "dataset": str(self.dataset),
            "output": str(self.output),
            "template": self.template,
            "reader": self.reader,
            "question_generator": self.question_generator,
            "language": self.language,
            "max_questions_per_document": self.max_questions_per_document,
            "recursive": self.recursive,
        }
        with path.open("w", encoding="utf-8") as handle:
            yaml.safe_dump(payload, handle, sort_keys=False)
