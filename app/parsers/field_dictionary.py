from __future__ import annotations
from app.adapters.rules import flat_extraction_rules
from rules.loader import load_template

FIELD_DEFINITIONS = flat_extraction_rules()
#FIELD_DEFINITIONS = load_template("erp").extraction_rules
print(type(FIELD_DEFINITIONS))
print(FIELD_DEFINITIONS)
# @dataclass(frozen=True)
# class FieldRule:
#     """A single named field and the regex pattern(s) that can extract it.
#
#     The first capturing group of the first pattern that matches is used as
#     the extracted value.
#     """
#
#     name: str
#     patterns: tuple[str, ...]

# FIELD_DEFINITIONS = {
#
#     "employee_name": {
#         "aliases": [
#             "employee",
#             "employee name",
#             "співробітник",
#             "працівник",
#         ],
#         "patterns": [
#             r"employee\s*:\s*(.+)",
#             r"співробітник\s*:\s*(.+)",
#         ],
#     },
#
#     "customer": {
#         "aliases": [
#             "customer",
#             "client",
#             "замовник",
#             "клієнт",
#         ],
#         "patterns": [
#             r"customer\s*:\s*(.+)",
#             r"замовник\s*:\s*(.+)",
#         ],
#     },
#
#     "salary": {
#         "aliases": [
#             "salary",
#             "зарплата",
#             "оклад",
#         ],
#         "patterns": [
#             r"salary\s*:\s*([\d\s]+)",
#             r"зарплата\s*:\s*([\d\s]+)",
#         ],
#     },
#
#     "passport": {
#         "aliases": [
#             "passport",
#             "паспорт",
#             "passport id",
#         ],
#         "patterns": [
#             r"passport.*?([A-Z]{2}\d{6})",
#             r"серії\s*([А-ЯІЇЄ]{2})\s*№?\s*(\d{6})",
#         ],
#     },
#
#     "contract_number": {
#         "aliases": [
#             "contract",
#             "Contract Number",
#         ],
#         "patterns": [
#             r"Contract Number:\s*([A-Z0-9\-]+)",
#             r"contract:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "valid_until": {
#         "aliases": [
#             "Contract Term",
#             "Valid Until",
#         ],
#         "patterns": [
#             r"Valid Until:\s*([A-Z0-9\-]+)",
#             r"Contract Term:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "contractor": {
#         "aliases": [
#             "Contractor",
#             "Supplier",
#
#         ],
#         "patterns": [
#             r"Contractor:\s*(.+)",
#             r"Supplier:\s*(.+)",
#
#         ],
#     },
#
#     "stage": {
#         "aliases": [
#             "Stage",
#             "Step",
#             "Етап",
#             "Стадія",
#
#         ],
#         "patterns": [
#             r"Stage:\s*(.+)",
#             r"Step:\s*(.+)",
#             r"Етап:\s*(.+)",
#             r"Стадія:\s*(.+)",
#         ],
#     },
#
#     "ticket_number": {
#         "aliases": [
#             "Ticket Number",
#         ],
#         "patterns": [
#             r"tkt-\d+",
#             r"ticket\s*number\s*:\s*(tkt-\d+)",
#         ],
#     },
#
#     "invoice_number": {
#         "aliases": [
#             "Invoice Number",
#         ],
#         "patterns": [
#             r"INV-\d+",
#         ],
#     },
#
#     "date": {
#         "aliases": [
#             "Дата",
#         ],
#         "patterns": [
#             r"Дата:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "month": {
#         "aliases": [
#             "Month",
#         ],
#         "patterns": [
#             r"Month:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "project": {
#         "aliases": [
#             "Project",
#             "Проєкт",
#         ],
#         "patterns": [
#             r"Project:\s*([A-Z0-9\-]+)",
#             r"Проєкт:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "asset": {
#         "aliases": [
#             "Asset",
#         ],
#         "patterns": [
#             r"Asset:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "department": {
#         "aliases": [
#             "Department",
#         ],
#         "patterns": [
#             r"Department:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "policy_number": {
#         "aliases": [
#             "Номер полиса:",
#             "Policy number:",
#         ],
#         "patterns": [
#             r"Номер полиса:\s*([A-Z0-9\-]+)",
#             r"Policy number:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "insured_person": {
#         "aliases": [
#             "INSURED PERSON:",
#
#         ],
#         "patterns": [
#             r"INSURED PERSON:\s*([A-Z0-9\-]+)",
#         ],
#     },
#
#     "agreement_number": {
#         "aliases": [
#             "Agreement Number",
#         ],
#         "patterns": [
#             r"AGR-\d+",
#         ],
#     },
#
#     "amount": {
#         "aliases": [
#             "Amount",
#             "Total",
#             "Total Due",
#             "Сума",
#         ],
#         "patterns": [
#             r"Total Due:\s*\$?([\d,]+(?:\.\d{2})?)",
#             r"Amount:\s*\$?([\d,]+(?:\.\d{2})?)",
#             r"Сума:\s*([\d,]+(?:\.\d{2})?)",
#         ],
#     },
#
#     "currency": {
#         "aliases": [
#             "Currency",
#             "Валюта",
#         ],
#         "patterns": [
#             r"Currency:\s*(USD|EUR|UAH|PLN|GBP)",
#             r"Валюта:\s*(USD|EUR|UAH|PLN|GBP)",
#         ],
#     },
#
#     "signed": {
#         "aliases": [
#             "Signed",
#         ],
#         "patterns": [
#             r"Signed:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
#         ],
#     },
# }
from app.adapters.rules import erp_template


# FIELD_DEFINITIONS: dict[str, tuple[FieldRule, ...]] = {
#     "Invoice": (
#         FieldRule("invoice_number", (r"invoice\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
#         FieldRule(
#             "customer",
#             (
#                 r"customer\s*:\s*([^\n]+)",
#                 r"bill\s*to\s*:\s*([^\n]+)",
#             ),
#         ),
#         FieldRule(
#             "amount",
#             patterns=(
#                 r"total\s*(?:due|amount)?\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
#                 r"amount\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
#                 r"сумма\s*[:\-]?\s*([\d,]+\.\d{2})",
#             ),
#         ),
#         FieldRule(
#             name="supplier",
#             patterns=(
#                 r"supplier\s*:\s*([^\n]+)",
#                 r"vendor\s*:\s*([^\n]+)",
#                 r"seller\s*:\s*([^\n]+)",
#             ),
#         ),
#         FieldRule(
#             "currency",
#             patterns=(
#                 r"amount.*?\b(USD|EUR|UAH|PLN|GBP)\b",
#                 r"\b(USD|EUR|UAH|PLN|GBP)\b",
#             ),
#         ),
#     ),
#     "Purchase Order": (
#         FieldRule(
#             "po_number",
#             (r"(?:p\.?o\.?|purchase\s*order)\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",),
#         ),
#         FieldRule("vendor", (r"vendor\s*(?:name)?\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule("amount", (r"total\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",)),
#     ),
#     "Vendor Profile": (
#         FieldRule("vendor", (r"vendor\s*name\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule("phone", (r"(?:phone|tel)\s*[:\-]?\s*([\d\-\+\(\) ]{7,})",)),
#         FieldRule("email", (r"([\w.\-]+@[\w.\-]+\.\w+)",)),
#         FieldRule("address", (r"address\s*[:\-]?\s*([^\n]+)",)),
#     ),
#     "Employment Contract": (
#         FieldRule("contract_number", (r"contract\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
#         FieldRule("contractor", (r"employer\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule(
#             "customer",
#             (
#                 r"customer\s*[:\-]?\s*([^\n]+)",
#                 r"bill\s*to\s*[:\-]?\s*([^\n]+)",
#             ),
#         ),
#         FieldRule(
#             "start_date",
#             (
#                 r"signed\s*:\s*([\d-]+)",
#                 r"start\s*date\s*:\s*([\d-]+)",
#             ),
#         ),
#         FieldRule(
#             "end_date",
#             (
#                 r"valid\s+until\s*:\s*([\d-]+)",
#                 r"end\s*date\s*:\s*([\d-]+)",
#             ),
#         ),
#     ),
#     "Generic Contract": (
#         FieldRule("contract_number", (r"contract\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
#         FieldRule("contractor", (r"contractor\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule(
#             "customer",
#             (
#                 r"customer\s*[:\-]?\s*([^\n]+)",
#                 r"client\s*[:\-]?\s*([^\n]+)",
#             ),
#         ),
#         FieldRule(
#             "start_date",
#             (
#                 r"signed\s*[:\-]?\s*([\d\-\.]+)",
#                 r"start\s*date\s*[:\-]?\s*([\d\-\.]+)",
#             ),
#         ),
#         FieldRule(
#             "end_date",
#             (
#                 r"valid\s*until\s*[:\-]?\s*([\d\-\.]+)",
#                 r"end\s*date\s*[:\-]?\s*([\d\-\.]+)",
#             ),
#         ),
#     ),
#     "Insurance Policy": (
#         FieldRule("policy_number", (r"policy\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
#         FieldRule("policy_holder", (r"policy\s*holder\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule("coverage_period", (r"coverage\s*period\s*[:\-]?\s*([^\n]+)",)),
#     ),
#     "Service Ticket": (
#         FieldRule("ticket_number", (r"ticket\s*(?:no|number|#)\s*[:\-]?\s*([A-Za-z0-9\-]+)",)),
#         FieldRule("status", (r"status\s*[:\-]?\s*([A-Za-z ]+)",)),
#         FieldRule("engineer", (r"(?:assigned\s*)?engineer\s*[:\-]?\s*([^\n]+)",)),
#     ),
#     "Bank Statement": (
#         FieldRule(
#             "account_number",
#             (
#                 r"номер\s+сч[её]та\s*[:\-]?\s*([A-Za-z0-9\-]+)",
#                 r"account\s*(?:number|no)\s*[:\-]?\s*([A-Za-z0-9\-]+)",
#                 r"account\s*#\s*([A-Za-z0-9\-]+)",
#             ),
#         ),
#         FieldRule(
#             "statement_period",
#             (
#                 r"statement\s*period\s*[:\-]?\s*([^\n]+)",
#                 r"период\s+выписки\s*[:\-]?\s*([^\n]+)",
#             ),
#         ),
#         FieldRule(
#             "balance",
#             (
#                 r"финальн\w*\s+баланс[\s\S]{0,120}?\$?([\d,]+\.\d{2})",
#                 r"closing\s+balance[\s\S]{0,80}?\$?([\d,]+\.\d{2})",
#                 r"final\s+balance[\s\S]{0,80}?\$?([\d,]+\.\d{2})",
#             ),
#         ),
#     ),
#     "CRM Opportunity": (
#         FieldRule("opportunity_name", (r"opportunity(?:\s*name)?\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule("stage", (r"(?:deal\s*)?stage\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule("value", (r"value\s*[:\-]?\s*([\d,]+(?:\.\d{2})?)",)),
#     ),
#     "Project Report": (
#         FieldRule("project_name", (r"project\s*(?:name)?\s*[:\-]?\s*([^\n]+)",)),
#         FieldRule("status", (r"status\s*[:\-]?\s*([A-Za-z ]+)",)),
#     ),
#     "Meeting Minutes": (
#         FieldRule("meeting_date", (r"date\s*[:\-]?\s*([\d/\-\.]+)",)),
#         FieldRule("attendees", (r"attendees\s*[:\-]?\s*([^\n]+)",)),
#     ),
# }