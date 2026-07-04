"""Generic, domain-agnostic template.

Useful as a default and as a starting point to copy when building a new
custom template. Relies entirely on the package's DEFAULT_RULES /
DEFAULT_FIELD_RULES for classification and extraction, and defines a
modest, broadly applicable set of question patterns.
"""

from __future__ import annotations

from rag_benchmark.generators.base import QuestionSpec, QuestionTemplateMap
from rag_benchmark.models import Difficulty

TEMPLATE_NAME = "generic"

QUESTION_TEMPLATES: QuestionTemplateMap = {
    "Invoice": [
        QuestionSpec(
            "What is the {field} on invoice {filename}?",
            requires_fields=("invoice_number", "amount", "customer", "currency"),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "metadata"),
        ),
    ],
    "Vendor Profile": [
        QuestionSpec(
            "What is the {field} of the vendor described in {filename}?",
            requires_fields=("vendor", "phone", "email", "address"),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "metadata"),
        ),
    ],
    "Generic Contract": [
        QuestionSpec(
            "What is the {field} in the contract {filename}?",
            requires_fields=("contract_number", "customer", "contractor", "start_date", "end_date"),
            difficulty=Difficulty.MEDIUM,
            tags=("retrieval", "metadata"),
        ),
        QuestionSpec(
            "Summarize the key terms of {filename}.",
            difficulty=Difficulty.HARD,
            tags=("summarization",),
        ),
    ],
    "Bank Statement": [
        QuestionSpec(
            "What is the {field} shown in {filename}?",
            requires_fields=("account_number", "statement_period", "balance"),
            difficulty=Difficulty.EASY,
            tags=("retrieval", "metadata"),
        ),
    ],
    "Meeting Minutes": [
        QuestionSpec(
            "Who attended the meeting recorded in {filename}?",
            requires_fields=("attendees",),
            difficulty=Difficulty.MEDIUM,
            tags=("retrieval",),
        ),
    ],
    "Project Report": [
        QuestionSpec(
            "What is the current {field} of the project in {filename}?",
            requires_fields=("project_name", "status"),
            difficulty=Difficulty.MEDIUM,
            tags=("retrieval", "metadata"),
        ),
    ],
}
