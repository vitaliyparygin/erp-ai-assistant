import re
from app.parsers.field_dictionary import FIELD_DEFINITIONS
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

    #
    # intent
    #

    q = question.lower()

    if any(x in q for x in ("зарплат", "salary")):
        metadata["intent"] = "salary"

    elif any(x in q for x in ("паспорт", "passport")):
        metadata["intent"] = "passport"

    elif any(x in q for x in ("тікет", "ticket")):
        metadata["intent"] = "ticket"

    elif any(x in q for x in ("інвойс", "invoice")):
        metadata["intent"] = "invoice"

    elif any(x in q for x in ("purchase order", "замовлен")):
        metadata["intent"] = "purchase_order"

    return metadata