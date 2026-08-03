from app.utils.resources import load_json

TERM_EXPANSIONS = load_json("term_expansions.json")
IMPORTANT_TERMS = load_json("important_terms_with_bust.json")
DOCUMENT_HINTS = load_json("document_hints.json")
REWRITE_MAP = load_json("rewrite_map.json")
FIELD_PATTERNS = load_json("field_patterns.json")
PROTECTED_TERMS = load_json("protected_terms.json")

RERANK_STOP_WORDS = frozenset(
    {
        "the",
        "is",
        "with",
        "which",
        "a",
        "an",
        "of",
        "to",
        "in",
    }
)

METADATA_FILTER_FIELDS = {
    "document_type",
    "document_id",
    "customer",
    "customer_name",
    "vendor",
    "contractor",
    "executor",
    "contract_number",
    "invoice_number",
    "purchase_order_number",
    "stage",
    "status",
    "person",
}

FIELD_HINTS = {
    "customer": ("customer:",),
    "customer_name": ("customer:",),
    "contractor": ("contractor:",),
    "executor": ("contractor:",),
    "vendor": ("vendor:",),
    "eic": ("eic:", "eic"),
    "stage": ("stage:",),
    "status": ("status:",),
}

FIELD_BOOSTS = {
    "customer": 0.40,
    "customer_name": 0.40,
    "contractor": 0.40,
    "executor": 0.40,
    "vendor": 0.40,
    "eic": 0.50,
    "stage": 0.40,
    "status": 0.40,
}
RERANK_FIELD_BOOSTS = {
    "eic": 0.50,
    "customer": 0.40,
    "contractor": 0.40,
    "executor": 0.40,
    "stage": 0.40,
    "contract_service_agreement": 0.50,
    "contract_number": 0.30,
    "contractor_field": 0.20,
    "customer_field": 0.10,
    "invoice_penalty_for_contract": -0.20,
}
MAX_CONTEXT = 20_000
