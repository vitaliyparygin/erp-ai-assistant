import re
from app.parsers.field_dictionary import FIELD_DEFINITIONS
from rules import detect_document_type

PERSON_PATTERNS = [
    r"[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+",
    r"[A-Z][a-z]+\s+[A-Z][a-z]+",
]


def extract_query_metadata(question: str) -> dict:
    metadata: dict[str, str] = {}

    normalized_question = question.strip()

    # Structured identifiers / explicit fields.
    for field_name, definition in FIELD_DEFINITIONS.items():
        for pattern in definition.patterns:
            match = re.search(
                pattern,
                normalized_question,
                re.IGNORECASE,
            )

            if not match:
                continue

            value = (match.group(1) if match.lastindex else match.group(0)).strip()

            if not value:
                continue

            metadata[definition.name] = value
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
