FIELD_DEFINITIONS = {

    "employee_name": {
        "aliases": [
            "employee",
            "employee name",
            "співробітник",
            "працівник",
        ],
        "patterns": [
            r"employee\s*:\s*(.+)",
            r"співробітник\s*:\s*(.+)",
        ],
    },

    "customer": {
        "aliases": [
            "customer",
            "client",
            "замовник",
            "клієнт",
        ],
        "patterns": [
            r"customer\s*:\s*(.+)",
            r"замовник\s*:\s*(.+)",
        ],
    },

    "salary": {
        "aliases": [
            "salary",
            "зарплата",
            "оклад",
        ],
        "patterns": [
            r"salary\s*:\s*([\d\s]+)",
            r"зарплата\s*:\s*([\d\s]+)",
        ],
    },

    "passport": {
        "aliases": [
            "passport",
            "паспорт",
            "passport id",
        ],
        "patterns": [
            r"passport.*?([A-Z]{2}\d{6})",
            r"серії\s*([А-ЯІЇЄ]{2})\s*№?\s*(\d{6})",
        ],
    },

    "contract_number": {
        "aliases": [
            "contract",
            "Contract Number",
        ],
        "patterns": [
            r"Contract Number:\s*([A-Z0-9\-]+)",
            r"contract:\s*([A-Z0-9\-]+)",
        ],
    },

    "valid_until": {
        "aliases": [
            "Contract Term",
            "Valid Until",
        ],
        "patterns": [
            r"Valid Until:\s*([A-Z0-9\-]+)",
            r"Contract Term:\s*([A-Z0-9\-]+)",
        ],
    },

    "contractor": {
        "aliases": [
            "Contractor",
            "Supplier",

        ],
        "patterns": [
            r"Contractor:\s*(.+)",
            r"Supplier:\s*(.+)",

        ],
    },

    "stage": {
        "aliases": [
            "Stage",
            "Step",
            "Етап",
            "Стадія",

        ],
        "patterns": [
            r"Stage:\s*(.+)",
            r"Step:\s*(.+)",
            r"Етап:\s*(.+)",
            r"Стадія:\s*(.+)",
        ],
    },

    "ticket_number": {
        "aliases": [
            "Ticket Number",
        ],
        "patterns": [
            r"ticket\s*number\s*:\s*(tkt-\d+)",
            r"\b(tkt-\d+)\b",
        ],
    },

    "invoice_number": {
        "aliases": [
            "Invoice Number",
        ],
        "patterns": [
            r"\bINV-\d+\b",
        ],
    },

    "date": {
        "aliases": [
            "Дата",
        ],
        "patterns": [
            r"Дата:\s*([A-Z0-9\-]+)",
        ],
    },

    "month": {
        "aliases": [
            "Month",
        ],
        "patterns": [
            r"Month:\s*([A-Z0-9\-]+)",
        ],
    },

    "project": {
        "aliases": [
            "Project",
            "Проєкт",
        ],
        "patterns": [
            r"Project:\s*([A-Z0-9\-]+)",
            r"Проєкт:\s*([A-Z0-9\-]+)",
        ],
    },

    "asset": {
        "aliases": [
            "Asset",
        ],
        "patterns": [
            r"Asset:\s*([A-Z0-9\-]+)",
        ],
    },

    "department": {
        "aliases": [
            "Department",
        ],
        "patterns": [
            r"Department:\s*([A-Z0-9\-]+)",
        ],
    },

    "policy_number": {
        "aliases": [
            "Номер полиса:",
            "Policy number:",
        ],
        "patterns": [
            r"Номер полиса:\s*([A-Z0-9\-]+)",
            r"Policy number:\s*([A-Z0-9\-]+)",
        ],
    },

    "insured_person": {
        "aliases": [
            "INSURED PERSON:",

        ],
        "patterns": [
            r"INSURED PERSON:\s*([A-Z0-9\-]+)",
        ],
    },

    "agreement_number": {
        "aliases": [
            "Agreement Number",
        ],
        "patterns": [
            r"AGR-\d+",
        ],
    },

    "hours": {
        "aliases": [
            "Hours",
        ],
        "patterns": [
            r"Hours:\s*(\d+)",
        ],
    },
    "overtime": {
        "aliases": [
            "Overtime",
        ],
        "patterns": [
            r"Overtime:\s*(\d+)",
        ],
    },
    "purchase_order": {
        "aliases": [
            "Purchase Order",
            "Purchase Order #",
            "Order Number",
        ],
        "patterns": [
            r"Purchase\s+Order\s*#?\s*(P\d+)",
            r"Order\s+Number\s*#?\s*(P\d+)",
            r"\bP\d+\b",
        ],
    }
}
