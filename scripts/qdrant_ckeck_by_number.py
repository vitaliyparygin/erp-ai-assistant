from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(url="http://localhost:6333")

collection = "erp_documents"

offset = None


for value in ["INT-2024-555", "int-2024-555"]:
    points, _ = client.scroll(
        collection_name="erp_documents",
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="contract_number",
                    match=MatchValue(value=value),
                )
            ]
        ),
        limit=10,
        with_payload=True,
    )

    print(value, "=>", len(points))
