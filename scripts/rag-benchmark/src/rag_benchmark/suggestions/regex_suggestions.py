import re
from collections import Counter
from rag_benchmark.diagnostics.models import  RegexCandidate

#: Field name -> alternative phrasings worth adding to an extraction regex.
#: A small, deliberately generic hint table — not meant to be exhaustive,
#: just enough to unblock a developer looking at a 0%-coverage field.
FIELD_SYNONYM_HINTS: dict[str, list[str]] = {
    "address": ["office", "registered office", "location"],
    "phone": ["telephone", "contact number", "mobile"],
    "email": ["e-mail", "contact email"],
    "amount": ["total", "sum", "balance due", "grand total"],
    "vendor": ["supplier", "seller", "provider"],
    "customer": ["client", "buyer", "account holder"],
    "start_date": ["effective date", "commencement date"],
    "end_date": ["expiration date", "termination date"],
    "status": ["state", "current status"],
    "engineer": ["technician", "assigned to"],
    "ticket_number": ["case number", "reference number"],
    "contract_number": ["agreement number", "reference number"],
}

def build_regex(label: str) -> str:
    escaped = re.escape(label)

    lower = label.lower()

    if "date" in lower:
        value = r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"

    elif any(x in lower for x in ("amount", "total", "balance", "price")):
        value = r"([$€£]?\s?[0-9][0-9,\.]*)"

    elif "email" in lower:
        value = r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"

    elif "phone" in lower:
        value = r"([\+\d][\d\-\(\)\s]{6,})"

    else:
        value = r"(.+)"

    return rf"{escaped}\s*[:\-]?\s*{value}"


def suggest_field_synonyms(field_name: str) -> list[str]:
    """Return alternative phrasings that might help extract a missing field."""
    return FIELD_SYNONYM_HINTS.get(field_name, ["(no synonym hints available — inspect a sample document)"])


@staticmethod
def build_regex_candidates(
        labels: Counter[str],
) -> list[RegexCandidate]:

    candidates = []

    for label, count in labels.most_common():
        candidates.append(
            RegexCandidate(
                label=label,
                count=count,
                regex=build_regex(label),
            )
        )

    return candidates


def escape_label(label: str) -> str:
    """
    Escape label for regex generation.

    Example:
        Invoice Number
        Invoice (Net)
        PO#
    """

    return re.escape(label)


def suggest_regex(label: str) -> str:
    """
    Generate a generic regex for a detected document label.

    Examples
    --------
    Customer
        -> Customer\\s*[:\\-]?\\s*(.+)

    Invoice Number
        -> Invoice\\ Number\\s*[:\\-]?\\s*(.+)

    Amount
        -> Amount\\s*[:\\-]?\\s*([$€£]?\\s?[0-9][0-9,.]*)

    Date
        -> Date\\s*[:\\-]?\\s*([0-9./\\-]+)

    Currency
        -> Currency\\s*[:\\-]?\\s*([A-Z]{3})
    """

    label = label.strip()

    escaped = escape_label(label)

    lower = label.lower()

    #
    # Amount / Total
    #
    if any(
        word in lower
        for word in (
            "amount",
            "total",
            "subtotal",
            "price",
            "balance",
            "cost",
        )
    ):
        value = r"([$€£]?\s?[0-9][0-9,.]*)"

    #
    # Date
    #
    elif "date" in lower:
        value = r"([0-9./\-]+)"

    #
    # Currency
    #
    elif "currency" in lower:
        value = r"([A-Z]{3})"

    #
    # Email
    #
    elif "email" in lower:
        value = (
            r"([A-Za-z0-9._%+-]+@"
            r"[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
        )

    #
    # Phone
    #
    elif "phone" in lower:
        value = r"([\+\d][\d\-\s()]+)"

    #
    # Number / ID
    #
    elif any(
        word in lower
        for word in (
            "number",
            "no",
            "id",
            "invoice",
            "order",
            "contract",
            "po",
        )
    ):
        value = r"([A-Za-z0-9\-_/]+)"

    #
    # default
    #
    else:
        value = r"(.+)"

    return rf"{escaped}\s*[:\-]?\s*{value}"

