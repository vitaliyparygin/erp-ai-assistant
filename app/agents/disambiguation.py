from __future__ import annotations
from rules.models import DocumentType
from rules import extract_metadata
from app.utils.messages import MESSAGES


def build_disambiguation_answer(
    query: str,
    chunks: list,
) -> str | None:
    contracts: dict[str, dict[str, str | None]] = {}

    for chunk in chunks:
        metadata = dict(chunk.metadata)
        document_type = metadata.get("document_type")

        if not isinstance(document_type, str):
            continue
        # if ingestion not found all rows, found it from rules
        extracted = extract_metadata(
            text=chunk.page_content,
            document_type=document_type,
        )
        metadata.update(extracted)

        if metadata.get("document_type") != DocumentType.CONTRACT:
            continue

        contracts[metadata["document_name"]] = {
            "contract_number": metadata.get("contract_number"),
            "valid_until": metadata.get("valid_until"),
        }

    if len(contracts) <= 1:
        return None

    return _render_contract_list(contracts)


def _render_contract_list(
    contracts: dict[str, dict[str, str | None]],
) -> str:
    lines = [
        MESSAGES["contract"]["found"],
        "",
    ]

    for index, (name, data) in enumerate(
        contracts.items(),
        start=1,
    ):
        lines.append(f"{index}. {name}")

        if number := data.get("contract_number"):
            lines.append(f"   Number: {number}")

        if valid_until := data.get("valid_until"):
            lines.append(f"   Valid until: {valid_until}")

        lines.append("")

    lines.append(MESSAGES["contract"]["clarify"])

    return "\n".join(lines)
