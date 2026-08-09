import asyncio
import sys
from pathlib import Path
from app.db.session import AsyncSessionLocal
from app.models.orm import DocumentModel
from app.workers.ingestion_worker import ingest_document
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentModel).order_by(DocumentModel.created_at)
        )
        documents = result.scalars().all()

    if not documents:
        print("No documents found in database.")
        return

    print(f"Found {len(documents)} documents.")

    for document in documents:
        document_id = str(document.id)
        file_path = document.file_path
        mime_type = document.mime_type
        filename = document.original_filename or document.filename

        print()
        print("=" * 80)
        print(f"Reindexing: {filename}")
        print(f"document_id: {document_id}")
        print(f"file_path:   {file_path}")
        print("=" * 80)

        if not Path(file_path).exists():
            print(f"SKIP: file does not exist: {file_path}")
            continue

        try:
            result = ingest_document(
                document_id=document_id,
                file_path=file_path,
                mime_type=mime_type,
                document_name=filename,
                original_filename=filename,
            )

            print(f"OK: {result}")

        except Exception as exc:
            print(f"ERROR: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
