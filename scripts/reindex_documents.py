import asyncio
import sys
from pathlib import Path
from app.models.orm import DocumentModel
from app.workers.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from sqlalchemy import select

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


async def main() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentModel).order_by(DocumentModel.original_filename)
        )
        documents = result.scalars().all()

    if not documents:
        print("⚠️ No documents found in database")
        return

    print(f"Found {len(documents)} documents")

    queued = 0
    skipped = 0

    for document in documents:
        file_path = Path(document.file_path)

        if not file_path.exists():
            print(
                f"⚠️ SKIP {document.original_filename}: "
                f"{document.file_path} does not exist"
            )
            skipped += 1
            continue

        task = celery_app.send_task(
            "app.workers.ingestion_worker.ingest_document",
            kwargs={
                "document_id": str(document.id),
                "file_path": str(document.file_path),
                "mime_type": document.mime_type,
                "document_name": document.original_filename,
                "original_filename": document.original_filename,
            },
        )

        print(f"📥 queued: {document.original_filename} " f"(task={task.id})")

        queued += 1

    print()
    print(f"✅ queued: {queued}")
    print(f"⚠️ skipped: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
