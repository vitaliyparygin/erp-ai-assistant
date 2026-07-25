import re
import traceback
from app.utils.resources import load_json

CONTRACT_TERMS = load_json("contract_keywords.json")

def _extract_contract_number(
    text: str,
) -> str | None:

    patterns = [
        r"Contract Number:\s*([A-Z0-9\-]+)",
        r"Номер договору:\s*([A-Z0-9\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return None



def _extract_valid_until(
    text: str,
) -> str | None:

    patterns = [
        r"Valid Until:\s*([0-9\-]+)",
        r"Діє до:\s*([0-9\-]+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return None


def build_disambiguation_answer(
    query: str,
    chunks: list,
) -> str | None:

    contracts = {}

    for chunk in chunks:

        md = chunk.metadata

        if md.get("document_type") != "contract":
            continue

        contracts[
            md["document_name"]
        ] = {
            "contract_number": md.get("contract_number"),
            "valid_until": md.get("valid_until"),
        }

    if len(contracts) <= 1:
        return None
    traceback.print_stack()
    lines = [
        "I found some contracts:",
        "",
    ]

    idx = 1

    for doc_name, data in contracts.items():

        lines.append(f"{idx}. {doc_name}")

        if data.get("contract_number"):
            lines.append(
                f"   Number: {data['contract_number']}"
            )

        if data.get("valid_until"):
            lines.append(
                f"   Valid until: {data['valid_until']}"
            )

        lines.append("")

        idx += 1

    lines.append(
        "Please clarify which contract you are talking about."
    )

    return "\n".join(lines)