# Plugin Guide: writing a custom template

A template configures everything domain-specific: which document types
exist, how to recognize them, which metadata to pull out, and which
questions to generate. You never modify `rag_benchmark` itself.

## Minimal template

Create a file, e.g. `my_company.py`, anywhere on disk:

```python
from rag_benchmark.generators.base import QuestionSpec, QuestionTemplateMap
from rag_benchmark.models import Difficulty

TEMPLATE_NAME = "my_company"

QUESTION_TEMPLATES: QuestionTemplateMap = {
    "Onboarding Doc": [
        QuestionSpec(
            "What is the {field} described in {filename}?",
            requires_fields=("policy_name",),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "hr"),
        ),
    ],
}
```

That's the entire required surface: a module-level `QUESTION_TEMPLATES`
dict. Run it with:

```bash
rag-benchmark generate --dataset ./docs --template ./my_company.py
```

Templates can be referenced three ways:

1. A built-in name: `--template erp`
2. A path to a `.py` file: `--template ./plugins/my_company.py`
3. An importable dotted module path: `--template mycompany.rag_template`
   (useful when the template ships inside another installed package)

## Adding classification rules

Without `CLASSIFICATION_RULES`, only document types the package already
recognizes generically (Invoice, Vendor Profile, Contract, ...) will be
classified — anything else stays `"Unknown"` and produces no questions.
To recognize a new document type:

```python
from rag_benchmark.classifier import ClassificationRule

CLASSIFICATION_RULES = (
    ClassificationRule(
        document_type="Onboarding Doc",
        filename_patterns=(r"onboarding", r"new[-_ ]?hire"),
        content_patterns=(r"welcome\s*to\s*the\s*team", r"first\s*day\s*checklist"),
    ),
)
```

`filename_patterns` and `content_patterns` are regexes checked
case-insensitively against the filename and full document text
respectively. A document is classified into whichever rule scores
highest; a document that matches nothing gets `document_type="Unknown"`.

## Adding extraction rules

```python
from rag_benchmark.extractor import FieldRule

EXTRACTION_RULES = {
    "Onboarding Doc": (
        FieldRule("policy_name", (r"policy\s*name\s*[:\-]?\s*([^\n]+)",)),
    ),
}
```

Each `FieldRule` has a field name and one or more regex patterns; the
first pattern with a capturing group that matches wins. Rules you define
here are *merged on top of* the package's generic rules — you don't need
to redefine fields for document types the generic extractor already
handles well (e.g. `Invoice`, `Bank Statement`).

## Writing question specs

```python
QuestionSpec(
    query_template="What is the {field} of {filename}?",
    requires_fields=("field_a", "field_b"),   # every field must have been extracted
    difficulty=Difficulty.MEDIUM,
    tags=("retrieval", "metadata"),
)
```

- If `requires_fields` is non-empty, `TemplateQuestionGenerator` renders
  **one question per field** (substituting `{field}` with the field's
  display name) — but only if *all* listed fields were successfully
  extracted from that document. This keeps generated questions honest:
  no question ever references a fact the extractor didn't actually find.
- If `requires_fields` is empty, the template renders once per document
  with just `{filename}` available — useful for summarization-style
  questions.
- Any extracted field name can also be interpolated directly, e.g.
  `"What is the total for {invoice_number}?"`.

## Using an LLM generator instead

`QUESTION_TEMPLATES` still governs which document types are in scope even
when using `LLMQuestionGenerator` — it just ignores the specs' text and
prompts an LLM with the document type and extracted metadata instead. Wire
it up as a library call:

```python
from rag_benchmark import BenchmarkPipeline, BenchmarkConfig
from rag_benchmark.generators.llm_generator import AnthropicLLMClient, LLMQuestionGenerator

pipeline = BenchmarkPipeline(generator=LLMQuestionGenerator(client=AnthropicLLMClient()))
pipeline.run(BenchmarkConfig.load("benchmark.yaml"))
```

## Reference implementation

`src/rag_benchmark/templates/erp.py` is a complete, non-trivial example
covering eight document types end-to-end — copy it as a starting point.
