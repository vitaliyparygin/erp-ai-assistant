import re

DOCUMENT_PATTERNS = [
    # exact filename
    (
        re.compile(
            r'([A-Za-z0-9 _\-]+?\.(?:pdf|docx|xlsx|csv))',
            re.IGNORECASE,
        ),
        "original_filename",
    ),

    # Purchase Order
    (
        re.compile(
            r'\bP\d{4,}\b',
            re.IGNORECASE,
        ),
        "purchase_order",
    ),

    # Invoice
    (
        re.compile(
            r'\bINV-\d+\b',
            re.IGNORECASE,
        ),
        "invoice_number",
    ),

    # Contract
    (
        re.compile(
            r'\b(?:SC|MC|ERP)-\d{4}-\d+\b',
            re.IGNORECASE,
        ),
        "contract_number",
    ),

    # Delivery Note
    (
        re.compile(
            r'\bDN-\d{4}-\d+\b',
            re.IGNORECASE,
        ),
        "delivery_note",
    ),
]
DOCUMENT_ALIASES = {
    "NDA Agreement.pdf": [
        "nda",
        "nda agreement",
        "non disclosure",
        "non-disclosure",
    ],

    "INSURANCE POLICY.pdf": [
        "insurance",
        "insurance policy",
        "policy",
        "страховий поліс",
        "страхового полісу",
        "страховому полісі",
        "страховка",
    ],

    "RENTAL AGREEMENT.pdf": [
        "rent",
        "rental",
        "lease",
        "договір оренди",
        "оренда",
    ],

    "EMPLOYMENT CONTRACT.pdf": [
        "employment contract",
        "employment",
        "трудовий договір",
        "контракт",
    ],

    "Invoice.pdf": [
        "invoice",
        "інвойс",
        "рахунок",
    ],

    "Leave Order.pdf": [
        "leave",
        "vacation",
        "відпустка",
        "leave order",
    ],
}
def extract_document_reference(question: str) -> dict:
    """
    Returns document hints from user query.

    Example:

    "qty in P00019"

    ->
    {
        "purchase_order": "P00019"
    }

    "where signed NDA Agreement"

    ->
    {
        "filename": "NDA Agreement.pdf"
    }
    """

    result = {}

    text = question.strip()
    q = question.lower()
    for filename, aliases in DOCUMENT_ALIASES.items():

        for alias in aliases:

            if alias.lower() in q:
                return filename


    for pattern, field in DOCUMENT_PATTERNS:

        m = pattern.search(text)

        if not m:
            continue

        value = m.group(1) if m.lastindex else m.group(0)

        if field == "original_filename":
            value = value.strip()

        result[field] = value

    #
    # Named document without extension
    #

    lower = text.lower()

    known_docs = [
        "nda agreement",
        "employment contract",
        "purchase order",
        "vendor profile",
        "salary statement",
        "meeting minutes",
        "project status report",
    ]

    for doc in known_docs:

        if doc in lower:

            result.setdefault(
                "original_filename",
                f"{doc.title().lower()}.pdf"
            )

    return result