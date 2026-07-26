import re
from app.parsers.field_dictionary import FIELD_DEFINITIONS
from rules import detect_document_type

PERSON_PATTERNS = [
    r"[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+\s+[А-ЯІЇЄҐ][а-яіїєґ']+",
    r"[A-Z][a-z]+\s+[A-Z][a-z]+",
]

def extract_query_metadata(question: str) -> dict:
    metadata = {}
    print("== extract_query_metadata ==")
    #
    # structured ids
    #
    for field_name, definition in FIELD_DEFINITIONS.items():
        for pattern in definition.patterns:

            m = re.search(
                pattern,
                question,
                re.IGNORECASE,
            )

            print(f"pattern: {pattern}, question: {question}, field: {definition}")
            print(m)
            if not m:
                continue

            print(definition)
            print(definition.name)

            if m.lastindex:
                value = m.group(1)
            else:
                value = m.group(0)

            metadata[definition.name] = value.strip()
            print(value)
            print(metadata)

            break

    #
    # person
    #

    for pattern in PERSON_PATTERNS:
        m = re.search(pattern, question)
        if m:
            metadata["person"] = m.group(0)
            break

    document_type = detect_document_type(
        text=question.lower(),
    )

    if document_type:
        metadata["document_type"] = document_type

    return metadata
