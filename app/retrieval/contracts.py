from app.core.logging import get_logger
from app.models.schemas import RetrievedChunk
from app.utils.resources import load_json
from rules.contract_patterns import CONTRACT_IDENTIFIER_RE

logger = get_logger(__name__)

REWRITE_MAP = load_json("rewrite_map.json")
FIELD_PATTERNS = load_json("field_patterns.json")
PROTECTED_TERMS = load_json("protected_terms.json")


def is_contract_query(query: str) -> bool:
    q = query.lower()
    keywords = load_json("contract_keywords.json")
    return any(k in q for k in keywords)


def has_contract_identifier(query: str) -> bool:
    return bool(CONTRACT_IDENTIFIER_RE.search(query))


def is_ambiguous_contract_query(query: str) -> bool:
    if not isinstance(query, str):
        return False

    return is_contract_query(query) and not has_contract_identifier(query)


def requires_contract_disambiguation(
    query: str,
    docs: list,
) -> bool:
    if not is_ambiguous_contract_query(query):
        return False
    logger.warning(
        "RETRIEVED_DOCS",
        docs=[
            {
                "doc": c.document_name,
                "score": c.score,
            }
            for c in docs[:10]
        ],
    )
    contract_docs = [
        d for d in docs if str(d.metadata.get("document_type")).lower() == "contract"
    ]

    return len(contract_docs) > 1


def get_unique_docs(
    reranked: list[RetrievedChunk],
) -> dict[str, RetrievedChunk]:
    unique_docs: dict[str, RetrievedChunk] = {}

    for chunk in reranked:
        unique_docs[chunk.document_name] = chunk

    return unique_docs


def build_contract_disambiguation(contracts):
    logger.debug("build_contract_disambiguation:start")

    logger.debug(
        "build_contract_disambiguation:len",
        len=len(contracts),
    )

    if not contracts:
        return None
    # traceback.print_stack()
    lines = ["I found some contracts:\n"]

    for idx, contract in enumerate(
        contracts,
        start=1,
    ):
        lines.append(f"{idx}. {contract['document_name']}")

        if contract.get("contract_number"):
            lines.append(f"   Number: {contract['contract_number']}")

        if contract.get("valid_until"):
            lines.append(f"   Valid until: {contract['valid_until']}")

        lines.append("")

    lines.append("Specify what you are talking about.")
    logger.debug(
        "build_contract_disambiguation:result",
        len=len(lines),
    )
    return "\n".join(lines)


def normalize_document_type(value) -> str:
    if value is None:
        return ""

    return str(value).lower()
