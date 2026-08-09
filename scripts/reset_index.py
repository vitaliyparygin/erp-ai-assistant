import asyncio

from qdrant_client import AsyncQdrantClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal


async def main() -> None:
    settings = get_settings()

    # PostgreSQL
    async with AsyncSessionLocal() as db:
        await db.execute(text("TRUNCATE document_chunks CASCADE;"))
        await db.commit()

    print("✅ document_chunks cleared")

    # Qdrant
    client = AsyncQdrantClient(url=settings.qdrant_url)

    try:
        exists = await client.collection_exists(
            settings.qdrant_collection_name
        )

        if exists:
            await client.delete_collection(
                settings.qdrant_collection_name
            )
            print(
                f"✅ Qdrant collection deleted: "
                f"{settings.qdrant_collection_name}"
            )
        else:
            print("ℹ️ Qdrant collection does not exist")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())