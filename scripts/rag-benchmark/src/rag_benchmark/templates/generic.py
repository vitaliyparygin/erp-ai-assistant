"""Generic, domain-agnostic template.

Useful as a default and as a starting point to copy when building a new
custom template. Relies entirely on the package's DEFAULT_RULES /
DEFAULT_FIELD_RULES for classification and extraction, and defines a
modest, broadly applicable set of question patterns.
"""

from __future__ import annotations

from rag_benchmark.generators.base import QuestionSpec, QuestionTemplateMap
from rag_benchmark.models import Difficulty, QuestionField

TEMPLATE_NAME = "generic"

QUESTION_TEMPLATES: QuestionTemplateMap = {
    "Invoice": [
        QuestionSpec(
            "What is the {field} on invoice {filename}?",
            fields=[
                QuestionField("invoice_number"),
                QuestionField("amount"),
                QuestionField("customer"),
                QuestionField("currency")
            ],
        ),
    ],
    "Vendor Profile": [
        QuestionSpec(
            "What is the {field} of the vendor described in {filename}?",
            fields=[
                QuestionField("vendor"),
                QuestionField("phone"),
                QuestionField("email"),
                QuestionField("address")
            ]
        ),
    ],
    "Generic Contract": [
        QuestionSpec(
            "What is the {field} in the contract {filename}?",
            fields=[
                QuestionField("contract_number"),
                QuestionField("customer"),
                QuestionField("contractor"),
                QuestionField("contend_dateractor"),
                QuestionField("start_date")
            ]
        ),
        QuestionSpec(
            "Summarize the key terms of {filename}.",
        ),
    ],
    "Bank Statement": [
        QuestionSpec(
            "What is the {field} shown in {filename}?",
            fields=[
                QuestionField("account_number"),
                QuestionField("statement_period"),
                QuestionField("balance"),
            ]
        ),
    ],
    "Meeting Minutes": [
        QuestionSpec(
            "Who attended the meeting recorded in {filename}?",
            fields=[
                QuestionField("attendees")
            ]
        ),
    ],
    "Project Report": [
        QuestionSpec(
            "What is the current {field} of the project in {filename}?",
            fields=[
                QuestionField("project_name"),
                QuestionField("status"),
            ]
        ),
    ],
}
