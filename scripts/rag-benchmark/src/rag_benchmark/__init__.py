"""rag_benchmark: framework-agnostic benchmark dataset generation for RAG systems.

Public API surface. Import from here for the common case; submodules
remain available for advanced/direct usage (custom readers, classifiers,
generators, etc.).
"""

from rag_benchmark.config import BenchmarkConfig
from rag_benchmark.models import (
    BenchmarkDataset,
    BenchmarkQuery,
    ClassifiedDocument,
    DatasetStatistics,
    Document,
    ValidationReport,
)
from rag_benchmark.pipeline import BenchmarkPipeline

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "BenchmarkConfig",
    "BenchmarkPipeline",
    "BenchmarkDataset",
    "BenchmarkQuery",
    "ClassifiedDocument",
    "DatasetStatistics",
    "Document",
    "ValidationReport",
]
