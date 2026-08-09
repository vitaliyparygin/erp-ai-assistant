import re
from collections.abc import Mapping
from rules import detect_document_type

NORMALIZED_METADATA_FIELDS = {
    "invoice_number",
    "contract_number",
    "po_number",
    "ticket_number",
    "employee_id",
}

PERSON_PATTERNS = [
    r"[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+",
    r"[A-Z][a-z]+\s+[A-Z][a-z]+",
]

QUERY_IDENTIFIER_PATTERNS = {
    "invoice_number": (r"\bINV-\d+(?:-\d+)*\b",),
    "contract_number": (
        r"\bC-\d+(?:-\d+)*\b",
        r"\bINT-\d{4}-\d+\b",
    ),
    "po_number": (r"\bPO-\d+(?:-\d+)*\b",),
}


def normalize_metadata_value(value: str) -> str:
    return value.strip().casefold()


def normalize_filter_metadata(
    metadata: Mapping[str, object],
) -> dict[str, object]:
    result = dict(metadata)

    for key in NORMALIZED_METADATA_FIELDS:
        value = result.get(key)

        if isinstance(value, str):
            result[key] = value.strip().casefold()

    return result


def extract_query_metadata(question: str) -> dict[str, str]:
    metadata: dict[str, str] = {}

    normalized_question = question.strip()

    # Explicit identifiers only.
    for field_name, patterns in QUERY_IDENTIFIER_PATTERNS.items():
        for pattern in patterns:
            match = re.search(
                pattern,
                normalized_question,
                re.IGNORECASE,
            )

            if match:
                metadata[field_name] = match.group(0)
                break

    # Person names.
    for pattern in PERSON_PATTERNS:
        match = re.search(pattern, normalized_question)

        if match:
            metadata["person"] = match.group(0).strip()
            break

    # Document type is a hint, not necessarily an exact constraint.
    document_type = detect_document_type(
        text=normalized_question.lower(),
    )

    if document_type:
        metadata["document_type"] = document_type

    return metadata
