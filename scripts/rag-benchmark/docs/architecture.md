# Architecture

## Pipeline overview

```
                 ┌────────────┐
   dataset/  ──▶ │  scanner   │  DocumentScanner: walk directory, tag file formats
                 └─────┬──────┘
                       │ ScannedFile[]
                       ▼
                 ┌────────────┐
                 │   reader   │  ReaderRegistry -> PDFReader / DocxReader / TxtReader / MarkdownReader
                 └─────┬──────┘
                       │ Document
                       ▼
                 ┌────────────┐
                 │ classifier │  DocumentClassifier -> DefaultClassifier (rule-based, filename + content)
                 └─────┬──────┘
                       │ ClassificationResult
                       ▼
                 ┌────────────┐
                 │ extractor  │  MetadataExtractor -> RegexMetadataExtractor (per document_type field rules)
                 └─────┬──────┘
                       │ ExtractedMetadata
                       ▼
              ClassifiedDocument (document + classification + metadata)
                       │
                       ▼
                 ┌────────────┐
                 │  generator │  QuestionGenerator -> TemplateQuestionGenerator | LLMQuestionGenerator
                 └─────┬──────┘
                       │ BenchmarkQuery[]
                       ▼
                 ┌────────────┐
                 │  metrics   │  compute_statistics() / validate_dataset()
                 └─────┬──────┘
                       │
                       ▼
                 ┌────────────┐
                 │  writers   │  json_writer / csv_writer / markdown_writer
                 └────────────┘
                       │
                       ▼
        benchmark_queries.json, retrieval_metrics.csv,
        latency_metrics.csv, benchmark_results_latest.md
```

`BenchmarkPipeline` (`pipeline.py`) is the only module that knows about all
of the above stages; it wires them together via constructor injection and
contains no business logic itself. Every other module has exactly one
responsibility and depends only on `models.py` and, where relevant, the
narrow interface of the stage before it.

## Where domain knowledge lives

Nothing above mentions ERP, medical, or legal concepts. Domain knowledge —
which document types exist, how to recognize them, which fields to pull
out, and which questions to ask — is entirely data, held in a
**template** (see `templates/__init__.py` and the Plugin Guide). A
template supplies:

- `CLASSIFICATION_RULES: tuple[ClassificationRule, ...]` (optional — falls
  back to the package's generic rule set)
- `EXTRACTION_RULES: dict[str, tuple[FieldRule, ...]]` (optional — merged
  on top of the generic field rules)
- `QUESTION_TEMPLATES: QuestionTemplateMap` (required — defines which
  document types are in scope for question generation and how to phrase
  questions for each)

`BenchmarkPipeline.classify_and_extract` builds a `DefaultClassifier` and
`RegexMetadataExtractor` from whatever the template provides, and the
generator only ever iterates `template.question_templates`, so a document
type the template doesn't mention simply never produces questions.

## Extension points (SOLID in practice)

| Interface | Default implementation | How to extend |
|---|---|---|
| `DocumentReader` | `PDFReader`, `DocxReader`, `TxtReader`, `MarkdownReader` | Implement `DocumentReader` and register it on a `ReaderRegistry` |
| `DocumentClassifier` | `DefaultClassifier` (regex rules) | Implement `DocumentClassifier`, e.g. an embedding- or LLM-based classifier |
| `MetadataExtractor` | `RegexMetadataExtractor` | Implement `MetadataExtractor`, e.g. an NER-based extractor |
| `QuestionGenerator` | `TemplateQuestionGenerator`, `LLMQuestionGenerator` | Implement `QuestionGenerator` |
| Template | `generic`, `erp`, `medical`, `legal` | Drop a new `.py` file anywhere and load it by path |

Every extension point is a small `ABC` in the relevant module
(`pdf_reader.py`, `classifier.py`, `extractor.py`,
`generators/base.py`), constructor-injected into `BenchmarkPipeline`, so
tests and callers can supply fakes without subclassing pipeline internals.

## Data contracts

All cross-module types are Pydantic models in `models.py`:
`ScannedFile → Document → ClassificationResult + ExtractedMetadata →
ClassifiedDocument → BenchmarkQuery → BenchmarkDataset`. Keeping these in
one module means every stage can be typed against a stable contract
without importing from sibling stages.
