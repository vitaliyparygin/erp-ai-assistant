#!/usr/bin/env python3

import argparse

from qdrant_client import QdrantClient

DEFAULT_HOST = "http://qdrant:6333"
LOCAL_HOST = "http://localhost:6333"

COLLECTION = "erp_documents"

NORMALIZED_FIELDS = {
    "invoice_number",
    "contract_number",
    "po_number",
    "ticket_number",
    "employee_id",
}

EXPECTED_METADATA_FIELDS = {
    "document_type",
    "invoice_number",
    "contract_number",
    "po_number",
    "ticket_number",
    "employee_id",
    "customer",
    "currency",
    "status",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Qdrant payload metadata.")

    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=(
            "Qdrant host. Default: %(default)s. "
            "Use '--host 1' or '--host http://localhost:6333' "
            "for local execution."
        ),
    )

    return parser.parse_args()


def resolve_host(host: str) -> str:
    if host == "1":
        return LOCAL_HOST

    return host.rstrip("/")


def main() -> None:
    args = parse_args()
    host = resolve_host(args.host)

    print(f"Qdrant: {host}")
    print(f"Collection: {COLLECTION}")
    print()

    client = QdrantClient(url=host)

    offset = None

    while True:
        points, offset = client.scroll(
            collection_name=COLLECTION,
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        metadata_stats = {
            field: {
                "total": 0,
                "normalized": 0,
                "non_normalized": [],
            }
            for field in NORMALIZED_FIELDS
        }

        suspicious_values = []

        for point in points:
            payload = point.payload or {}
            # if payload.get("original_filename") == "gas_bill.pdf":
            #     print()
            #     print("GAS BILL PAYLOAD")
            #     print(point.id)
            #     print(payload)
            for field in NORMALIZED_FIELDS:
                value = payload.get(field)

                if not isinstance(value, str) or not value:
                    continue

                metadata_stats[field]["total"] += 1

                normalized = value.strip().casefold()

                if value == normalized:
                    metadata_stats[field]["normalized"] += 1
                else:
                    metadata_stats[field]["non_normalized"].append(
                        {
                            "point_id": str(point.id),
                            "field": field,
                            "value": value,
                            "expected": normalized,
                            "document": payload.get("original_filename"),
                        }
                    )

            invoice_number = payload.get("invoice_number")

            if invoice_number == "customer":
                suspicious_values.append(
                    {
                        "point_id": str(point.id),
                        "field": "invoice_number",
                        "value": invoice_number,
                        "document": payload.get("original_filename"),
                        "document_id": payload.get("document_id"),
                    }
                )

        if offset is None:
            break
    print()
    print("=" * 70)
    print(" METADATA NORMALIZATION")
    print("=" * 70)

    for field, stats in metadata_stats.items():
        total = stats["total"]
        normalized = stats["normalized"]
        bad = len(stats["non_normalized"])

        print(
            f"{field:<25}"
            f"total={total:<6}"
            f"normalized={normalized:<6}"
            f"non_normalized={bad}"
        )

        for item in stats["non_normalized"][:10]:
            print(
                f"  ⚠️ {item['document']}: "
                f"{item['value']!r} -> {item['expected']!r}"
            )

    print()
    print("=" * 70)
    print(" SUSPICIOUS METADATA")
    print("=" * 70)

    if suspicious_values:
        for item in suspicious_values[:20]:
            print(
                f"⚠️ {item['document']} | "
                f"{item['field']}={item['value']!r} | "
                f"point={item['point_id']}"
            )
    else:
        print("✅ No suspicious metadata values found")


if __name__ == "__main__":
    main()
