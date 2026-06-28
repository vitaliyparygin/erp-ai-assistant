import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.db.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as db:

        await db.execute(
            text("""
                TRUNCATE document_chunks CASCADE;
            """)
        )

        await db.execute(
            text("""
                TRUNCATE documents CASCADE;
            """)
        )

        await db.commit()

        print("✅ document_chunks очищено")
        print("✅ documents очищено")


if __name__ == "__main__":
    asyncio.run(main())