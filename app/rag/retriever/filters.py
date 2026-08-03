from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
)

from app.config.constants import METADATA_FILTER_FIELDS
from qdrant_client.models import Condition
from typing import TypedDict


class QueryMetadata(TypedDict, total=False):
    document_type: str
    document_number: str
    contract_number: str
    invoice_number: str
    purchase_order_number: str
    customer_name: str
    vendor: str
    person: str
    eic: str
    stage: str
    status: str


def build_retrieval_filter(
    *,
    query_metadata: QueryMetadata | None = None,
    document_ids: list[str] | None = None,
) -> Filter | None:
    """Build a Qdrant filter for document and metadata constraints."""

    must: list[Condition] = []

    if document_ids:
        must.append(
            FieldCondition(
                key="document_id",
                match=MatchAny(any=document_ids),
            )
        )

    if query_metadata:
        for key, value in query_metadata.items():
            if key not in METADATA_FILTER_FIELDS:
                continue

            if value is None or value == "":
                continue
            if not isinstance(value, (str, int, bool)):
                continue
            must.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value),
                )
            )

    if not must:
        return None

    return Filter(must=must)
