"""Legal Assistant domain template (example plugin)."""

from __future__ import annotations

from rag_benchmark.classifier import ClassificationRule
from rag_benchmark.extractor import FieldRule
from rag_benchmark.generators.base import QuestionSpec, QuestionTemplateMap
from rag_benchmark.models import Difficulty

TEMPLATE_NAME = "legal"

CLASSIFICATION_RULES: tuple[ClassificationRule, ...] = (
    ClassificationRule(
        document_type="NDA",
        filename_patterns=(r"nda", r"non[-_ ]?disclosure"),
        content_patterns=(r"non[-\s]?disclosure\s*agreement", r"confidential\s*information"),
    ),
    ClassificationRule(
        document_type="Litigation Brief",
        filename_patterns=(r"brief", r"litigation"),
        content_patterns=(r"plaintiff", r"defendant", r"court\s*of"),
    ),
    ClassificationRule(
        document_type="Contract",
        filename_patterns=(r"contract", r"agreement"),
        content_patterns=(r"this\s*agreement", r"parties\s*hereto", r"governing\s*law"),
    ),
    ClassificationRule(
        document_type="Power of Attorney",
        filename_patterns=(r"power[-_ ]?of[-_ ]?attorney", r"\bpoa\b"),
        content_patterns=(r"power\s*of\s*attorney", r"attorney[-\s]?in[-\s]?fact"),
    ),
)

EXTRACTION_RULES: dict[str, tuple[FieldRule, ...]] = {
    "NDA": (
        FieldRule("effective_date", (r"effective\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
        FieldRule("disclosing_party", (r"disclosing\s*party\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("receiving_party", (r"receiving\s*party\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Litigation Brief": (
        FieldRule("plaintiff", (r"plaintiff\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("defendant", (r"defendant\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("court", (r"court\s*of\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Contract": (
        FieldRule("governing_law", (r"governing\s*law\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("start_date", (r"start\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
        FieldRule("end_date", (r"end\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
    "Power of Attorney": (
        FieldRule("principal", (r"principal\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("agent", (r"agent\s*[:\-]?\s*([^\n]+)",)),
    ),
}

QUESTION_TEMPLATES: QuestionTemplateMap = {
    "NDA": [
        QuestionSpec(
            "What is the {field} of the NDA in {filename}?",
            requires_fields=("effective_date", "disclosing_party", "receiving_party"),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "legal", "metadata"),
        ),
    ],
    "Litigation Brief": [
        QuestionSpec(
            "Who is the {field} named in {filename}?",
            requires_fields=("plaintiff", "defendant"),
            difficulty=Difficulty.MEDIUM,
            tags=("retrieval", "legal", "metadata"),
        ),
    ],
    "Contract": [
        QuestionSpec(
            "What is the {field} specified in contract {filename}?",
            requires_fields=("governing_law", "start_date", "end_date"),
            difficulty=Difficulty.MEDIUM,
            tags=("retrieval", "legal", "metadata"),
        ),
    ],
    "Power of Attorney": [
        QuestionSpec(
            "Who is the {field} in the power of attorney {filename}?",
            requires_fields=("principal", "agent"),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "legal", "metadata"),
        ),
    ],
}
