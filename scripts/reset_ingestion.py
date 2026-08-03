import asyncio
import sys
from pathlib import Path
from sqlalchemy import text
from app.db.session import AsyncSessionLocal

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
                TRUNCATE document_chunks CASCADE;
            """))

        await db.execute(text("""
                TRUNCATE documents CASCADE;
            """))

        await db.commit()

        print("✅ document_chunks clear")
        print("✅ documents clear")


if __name__ == "__main__":
    asyncio.run(main())
