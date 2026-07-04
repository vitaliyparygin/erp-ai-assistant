"""Medical RAG domain template (example plugin).

Demonstrates how a second, unrelated domain plugs into the same core
pipeline as the ERP template — no shared code required beyond the
generic interfaces.
"""

from __future__ import annotations

from rag_benchmark.classifier import ClassificationRule
from rag_benchmark.extractor import FieldRule
from rag_benchmark.generators.base import QuestionSpec, QuestionTemplateMap
from rag_benchmark.models import Difficulty

TEMPLATE_NAME = "medical"

CLASSIFICATION_RULES: tuple[ClassificationRule, ...] = (
    ClassificationRule(
        document_type="Patient Record",
        filename_patterns=(r"patient", r"chart"),
        content_patterns=(r"patient\s*(id|name)", r"date\s*of\s*birth", r"diagnosis"),
    ),
    ClassificationRule(
        document_type="Lab Report",
        filename_patterns=(r"lab[-_ ]?report", r"lab[-_ ]?result"),
        content_patterns=(r"lab\s*(results?|report)", r"reference\s*range", r"specimen"),
    ),
    ClassificationRule(
        document_type="Prescription",
        filename_patterns=(r"prescription", r"\brx\b"),
        content_patterns=(r"prescri(bed|ption)", r"dosage", r"refills?"),
    ),
    ClassificationRule(
        document_type="Discharge Summary",
        filename_patterns=(r"discharge",),
        content_patterns=(r"discharge\s*summary", r"admission\s*date", r"discharge\s*date"),
    ),
)

EXTRACTION_RULES: dict[str, tuple[FieldRule, ...]] = {
    "Patient Record": (
        FieldRule("patient_id", (r"patient\s*id\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("diagnosis", (r"diagnosis\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("date_of_birth", (r"date\s*of\s*birth\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
    "Lab Report": (
        FieldRule("specimen", (r"specimen\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("test_name", (r"test\s*(?:name)?\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("result", (r"result\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Prescription": (
        FieldRule("medication", (r"medication\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("dosage", (r"dosage\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("refills", (r"refills?\s*[:\-]?\s*(\d+)",)),
    ),
    "Discharge Summary": (
        FieldRule("admission_date", (r"admission\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
        FieldRule("discharge_date", (r"discharge\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
}

QUESTION_TEMPLATES: QuestionTemplateMap = {
    "Patient Record": [
        QuestionSpec(
            "What is the {field} recorded for the patient in {filename}?",
            requires_fields=("patient_id", "diagnosis", "date_of_birth"),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "medical", "metadata"),
        ),
    ],
    "Lab Report": [
        QuestionSpec(
            "What is the {field} reported in {filename}?",
            requires_fields=("specimen", "test_name", "result"),
            difficulty=Difficulty.MEDIUM,
            tags=("retrieval", "medical", "metadata"),
        ),
    ],
    "Prescription": [
        QuestionSpec(
            "What is the {field} listed on the prescription in {filename}?",
            requires_fields=("medication", "dosage", "refills"),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "medical", "metadata"),
        ),
    ],
    "Discharge Summary": [
        QuestionSpec(
            "What is the {field} in the discharge summary {filename}?",
            requires_fields=("admission_date", "discharge_date"),
            difficulty=Difficulty.MEDIUM,
            tags=("retrieval", "medical", "metadata"),
        ),
    ],
}