EMPLOYEE_WORDS = {
    "робота",
    "звільнення",
    "останній",
    "працівник",
    "employee",
    "termination",
    "leave",
}

PHONE_WORDS = {
    "телефон",
    "phone",
    "mobile",
}

EMAIL_WORDS = {
    "email",
    "mail",
}

PASSPORT_WORDS = {
    "passport",
    "паспорт",
}

EIC_WORDS = {
    "eic",
}

INVOICE_WORDS = {
    "invoice",
    "інвойс",
    "рахунок",
}
SYNONYMS = {
    "telegram": [
        "telegram",
        "viber",
        "whatsapp",
        "messenger",
    ],

    "телеграм": [
        "telegram",
        "viber",
        "whatsapp",
    ],

    "підтримка": [
        "support",
        "assistance",
        "helpdesk",
        "24/7",
    ],

    "support": [
        "support",
        "assistance",
        "helpdesk",
    ],

    "звільняється": [
        "termination",
        "terminated",
        "leave",
        "employee",
    ],

    "звільнення": [
        "termination",
        "terminated",
        "leave",
    ],

    "останній": [
        "last",
        "end",
    ],

    "роботи": [
        "employment",
        "employee",
    ],
}

def expand_query(query: str) -> str:
    q = query.lower()

    extra = []

    if any(w in q for w in EMPLOYEE_WORDS):
        extra += [
            "employee",
            "employment",
            "termination",
            "leave",
            "last working day",
        ]

    if any(w in q for w in PHONE_WORDS):
        extra += [
            "phone",
            "mobile",
            "contact",
        ]

    if any(w in q for w in EMAIL_WORDS):
        extra += [
            "email",
            "mail",
        ]

    if any(w in q for w in PASSPORT_WORDS):
        extra += [
            "passport",
            "id",
        ]

    if any(w in q for w in EIC_WORDS):
        extra += [
            "eic",
            "electricity",
        ]

    if any(w in q for w in INVOICE_WORDS):
        extra += [
            "invoice",
            "status",
        ]
    expanded = [query]
    for key, values in SYNONYMS.items():

        if key in q:
            expanded.extend(values)

    return query + "\n" + "\n".join(sorted(set(expanded)))
