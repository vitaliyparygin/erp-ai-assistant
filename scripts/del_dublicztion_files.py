from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(
    host="localhost",
    port=6333,
)

duplicate_ids = [
    "daf324dc-da40-46c8-9695-10cfe1912e23",
    "d806e83e-4736-45e7-9d1f-b06dcad4d45a",
]

for doc_id in duplicate_ids:
    client.delete(
        collection_name="erp_documents",
        points_selector=Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=doc_id),
                )
            ]
        ),
    )

print("Done")