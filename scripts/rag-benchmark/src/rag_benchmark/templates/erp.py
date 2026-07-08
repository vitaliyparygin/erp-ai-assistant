"""ERP domain template.

Reference plugin demonstrating how a full domain (AI ERP Assistant) is
configured entirely through template data, with zero changes to core
rag_benchmark code. Covers Purchase Orders, Invoices, Contracts, Vendor
Profiles, Service Tickets, CRM Opportunities, Projects, and Employees.

This module intentionally lives under rag_benchmark.templates for
discoverability as the reference example, but nothing here is imported by
core modules — it is loaded on demand via `templates.load_template("erp")`,
exactly like an external plugin would be.
"""

from __future__ import annotations

from rag_benchmark.classifier import ClassificationRule
from rag_benchmark.extractor import FieldRule
from rag_benchmark.generators.base import QuestionSpec, QuestionTemplateMap
from rag_benchmark.models import Difficulty, QuestionField

TEMPLATE_NAME = "erp"

CLASSIFICATION_RULES: tuple[ClassificationRule, ...] = (
    ClassificationRule(
        document_type="Purchase Order",
        filename_patterns=(r"purchase[-_ ]?order", r"\bpo[-_]?\d+"),
        content_patterns=(r"purchase\s*order", r"\bp\.?o\.?\s*(no|number|#)"),
    ),
    ClassificationRule(
        document_type="Invoice",
        filename_patterns=(r"invoice", r"\binv[-_]?\d+"),
        content_patterns=(r"invoice\s*(no|number|#)", r"total\s*due", r"bill\s*to"),
    ),
    ClassificationRule(
        document_type="Contract",
        filename_patterns=(r"contract", r"msa", r"agreement"),
        content_patterns=(r"this\s*agreement", r"parties\s*hereto", r"effective\s*date"),
    ),
    ClassificationRule(
        document_type="Vendor Profile",
        filename_patterns=(r"vendor", r"supplier"),
        content_patterns=(r"vendor\s*(name|profile|id)", r"supplier\s*information"),
    ),
    ClassificationRule(
        document_type="Service Ticket",
        filename_patterns=(r"ticket", r"service[-_ ]?request"),
        content_patterns=(r"ticket\s*(no|number|#)", r"assigned\s*engineer", r"priority\s*:"),
    ),
    ClassificationRule(
        document_type="CRM Opportunity",
        filename_patterns=(r"opportunity", r"\bcrm\b", r"deal"),
        content_patterns=(r"opportunity\s*(name|stage|value)", r"deal\s*stage"),
    ),
    ClassificationRule(
        document_type="Project",
        filename_patterns=(r"project",),
        content_patterns=(r"project\s*(status|milestones|deliverables)",),
    ),
    ClassificationRule(
        document_type="Employee",
        filename_patterns=(r"employee", r"hr[-_ ]?record"),
        content_patterns=(r"employee\s*id", r"department\s*:", r"hire\s*date"),
    ),
)

EXTRACTION_RULES: dict[str, tuple[FieldRule, ...]] = {
    "Purchase Order": (
        FieldRule("po_number", (r"(?:p\.?o\.?|purchase\s*order)\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("vendor", (r"vendor\s*(?:name)?\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("amount", (r"total\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
        FieldRule("delivery_date", (r"delivery\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
    "Invoice": (
        FieldRule("invoice_number", (r"invoice\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("amount", (r"total\s*(?:due|amount)?\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
        FieldRule("customer", (r"bill\s*to\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("currency", (r"\b(USD|EUR|GBP|UAH|PLN)\b",)),
        FieldRule("due_date", (r"due\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
    "Contract": (
        FieldRule("contract_number", (r"contract\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("customer", (r"client\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("contractor", (r"contractor\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("start_date", (r"start\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
        FieldRule("end_date", (r"end\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
    "Vendor Profile": (
        FieldRule("vendor", (r"vendor\s*name\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("phone", (r"(?:phone|tel)\s*[:\-]?\s*([\d\-\+\(\) ]{7,})",)),
        FieldRule("email", (r"([\w.\-]+@[\w.\-]+\.\w+)",)),
        FieldRule("address", (r"address\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Service Ticket": (
        FieldRule("ticket_number", (r"ticket\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("status", (r"status\s*[:\-]?\s*([A-Za-z ]+)",)),
        FieldRule("engineer", (r"(?:assigned\s*)?engineer\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("priority", (r"priority\s*[:\-]?\s*([A-Za-z]+)",)),
    ),
    "CRM Opportunity": (
        FieldRule("opportunity_name", (r"opportunity\s*name\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("stage", (r"(?:deal\s*)?stage\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("value", (r"value\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
    ),
    "Project": (
        FieldRule("project_name", (r"project\s*(?:name)?\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("status", (r"status\s*[:\-]?\s*([A-Za-z ]+)",)),
        FieldRule("manager", (r"(?:project\s*)?manager\s*[:\-]?\s*([^\n]+)",)),
    ),
    "Employee": (
        FieldRule("employee_id", (r"employee\s*id\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
        FieldRule("department", (r"department\s*[:\-]?\s*([^\n]+)",)),
        FieldRule("hire_date", (r"hire\s*date\s*[:\-]?\s*([\d/\-\.]+)",)),
    ),
}

QUESTION_TEMPLATES: QuestionTemplateMap = {
    "Purchase Order": [
        QuestionSpec(
            "What is the {field} on purchase order {filename}?",
            fields=[
                QuestionField("po_number"),
                QuestionField("vendor"),
                QuestionField("amount"),
                QuestionField("amoudelivery_datent"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
    "Invoice": [
        QuestionSpec(
            "What is the {field} on invoice {filename}?",
            fields=[
                QuestionField("invoice_number"),
                QuestionField("amount"),
                QuestionField("customer"),
                QuestionField("currency"),
                QuestionField("due_date"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
    "Contract": [
        QuestionSpec(
            "What is the {field} in contract {filename}?",
            fields=[
                QuestionField("contract_number"),
                QuestionField("customer"),
                QuestionField("contractor"),
                QuestionField("start_date"),
                QuestionField("end_date"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
    "Vendor Profile": [
        QuestionSpec(
            "What is the {field} of the vendor in {filename}?",
            fields=[
                QuestionField("vendor"),
                QuestionField("phone"),
                QuestionField("email"),
                QuestionField("address"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
    "Service Ticket": [
        QuestionSpec(
            "What is the {field} for service ticket {filename}?",
            fields=[
                QuestionField("ticket_number"),
                QuestionField("status"),
                QuestionField("engineer"),
                QuestionField("priority"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
    "CRM Opportunity": [
        QuestionSpec(
            "What is the {field} of the opportunity in {filename}?",
            fields=[
                QuestionField("opportunity_name"),
                QuestionField("stage"),
                QuestionField("value"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
    "Project": [
        QuestionSpec(
            "What is the {field} of the project described in {filename}?",
            fields=[
                QuestionField("project_name"),
                QuestionField("status"),
                QuestionField("manager"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
    "Employee": [
        QuestionSpec(
            "What is the {field} for the employee record in {filename}?",
            fields=[
                QuestionField("employee_id"),
                QuestionField("department"),
                QuestionField("hire_date"),
            ],
            tags=("retrieval", "erp", "metadata"),
        ),
    ],
}