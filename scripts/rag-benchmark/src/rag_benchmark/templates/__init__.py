"""Template plugin system.

A "template" configures domain-specific behavior (which document types
exist, how to classify them, which metadata fields to extract, and which
questions to generate) without touching core package code. This is what
lets rag-benchmark stay framework/domain agnostic while still shipping a
ready-to-use ERP template, a medical template, etc.

A template is just a Python module exposing some of the following
module-level names:

    QUESTION_TEMPLATES: QuestionTemplateMap        (required)
    CLASSIFICATION_RULES: tuple[ClassificationRule, ...]   (optional)
    EXTRACTION_RULES: dict[str, tuple[FieldRule, ...]]     (optional)

Built-in templates live in this package (generic, erp, medical, legal).
Custom templates can be loaded from any file path, so a user can drop a
`my_company.py` next to their config and reference it with
`--template ./my_company.py` or `--template my_company` if it's on the
Python path, with zero changes to rag_benchmark itself.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from rag_benchmark.classifier import ClassificationRule
from rag_benchmark.extractor import FieldRule
from rag_benchmark.generators.base import QuestionTemplateMap
from rag_benchmark.utils import get_logger

logger = get_logger("templates")

_BUILTIN_TEMPLATES = {"generic", "erp", "medical", "legal"}


@dataclass(frozen=True)
class TemplateDefinition:
    """Fully resolved template, ready to hand to classifier/extractor/generator."""

    name: str
    question_templates: QuestionTemplateMap
    classification_rules: tuple[ClassificationRule, ...] = field(default_factory=tuple)
    extraction_rules: dict[str, tuple[FieldRule, ...]] = field(default_factory=dict)


def _load_module(name_or_path: str) -> ModuleType:
    candidate_path = Path(name_or_path)
    if candidate_path.suffix == ".py" and candidate_path.exists():
        module_name = f"rag_benchmark_plugin_{candidate_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, candidate_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load template plugin from {candidate_path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        logger.info("Loaded external template plugin: %s", candidate_path)
        return module

    if name_or_path in _BUILTIN_TEMPLATES:
        return importlib.import_module(f"rag_benchmark.templates.{name_or_path}")

    # Fall back to treating it as an importable dotted module path, so
    # templates can also be shipped as part of another installed package.
    try:
        module = importlib.import_module(name_or_path)
        logger.info("Loaded external template plugin from module: %s", name_or_path)
        return module
    except ImportError as exc:
        raise ValueError(
            f"Unknown template '{name_or_path}'. Expected one of "
            f"{sorted(_BUILTIN_TEMPLATES)}, a path to a .py file, or an "
            "importable module path."
        ) from exc


def load_template(name_or_path: str) -> TemplateDefinition:
    """Load a template by built-in name, file path, or dotted module path.

    Args:
        name_or_path: One of "generic", "erp", "medical", "legal"; a
            filesystem path to a plugin .py file; or a dotted module path
            importable from the current environment.

    Returns:
        A resolved TemplateDefinition.

    Raises:
        ValueError: If the template cannot be found or is missing the
            required QUESTION_TEMPLATES attribute.
    """
    module = _load_module(name_or_path)

    question_templates: QuestionTemplateMap | None = getattr(module, "QUESTION_TEMPLATES", None)
    if question_templates is None:
        raise ValueError(
            f"Template module '{module.__name__}' must define QUESTION_TEMPLATES"
        )

    classification_rules: tuple[ClassificationRule, ...] = getattr(
        module, "CLASSIFICATION_RULES", ()
    )
    extraction_rules: dict[str, tuple[FieldRule, ...]] = getattr(module, "EXTRACTION_RULES", {})

    display_name = getattr(module, "TEMPLATE_NAME", Path(name_or_path).stem)

    return TemplateDefinition(
        name=display_name,
        question_templates=question_templates,
        classification_rules=classification_rules,
        extraction_rules=extraction_rules,
    )


def available_builtin_templates() -> list[str]:
    """Return the names of templates bundled with the package."""
    return sorted(_BUILTIN_TEMPLATES)
