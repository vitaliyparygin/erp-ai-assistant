#!/usr/bin/env python3
"""
scripts/check_ingestion.py

Checks document ingestion pipeline health.

Usage:

docker compose exec backend python scripts/check_ingestion.py
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from sqlalchemy import func, select

from app.models.orm import DocumentChunkModel, DocumentModel
from app.db.session import AsyncSessionLocal
from app.rag.embeddings import EmbeddingService
from app.rag.retriever import VectorRetriever
from qdrant_client import AsyncQdrantClient
from app.core.config import get_settings

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

settings = get_settings()


GREEN = "✅"
RED = "❌"
YELLOW = "⚠️"


def row(name: str, value):
    print(f"{name:<35}{value}")


async def run():

    ok = True

    async with AsyncSessionLocal() as db:

        print()
        print("=" * 65)
        print(" INGESTION HEALTH")
        print("=" * 65)
        print()

        #
        # document statistics
        #

        status_rows = (
            await db.execute(
                select(
                    DocumentModel.status,
                    func.count()
                )
                .group_by(DocumentModel.status)
            )
        ).all()

        status = defaultdict(int)

        for s, c in status_rows:
            status[s] = c

        total_documents = (
            await db.scalar(
                select(func.count())
                .select_from(DocumentModel)
            )
        )

        total_chunks = (
            await db.scalar(
                select(func.count())
                .select_from(DocumentChunkModel)
            )
        )

        print("Documents")
        print("-" * 65)

        row("Indexed", status["indexed"])
        row("Pending", status["pending"])
        row("Processing", status["processing"])
        row("Failed", status["failed"])
        row("Total", total_documents)

        print()

        #
        # chunks
        #

        print("Chunks")
        print("-" * 65)

        row("PostgreSQL chunks", total_chunks)

        #
        # indexed documents without chunks
        #

        indexed_without_chunks = (
            await db.execute(
                select(DocumentModel.original_filename)
                .outerjoin(
                    DocumentChunkModel,
                    DocumentChunkModel.document_id == DocumentModel.id,
                )
                .where(DocumentModel.status == "indexed")
                .group_by(
                    DocumentModel.id,
                    DocumentModel.original_filename,
                )
                .having(func.count(DocumentChunkModel.id) == 0)
            )
        ).all()

        print()

        #
        # chunks without qdrant id
        #

        missing_vectors = (
            await db.scalar(
                select(func.count())
                .select_from(DocumentChunkModel)
                .where(DocumentChunkModel.qdrant_point_id.is_(None))
            )
        )

        #
        # qdrant
        #

        client = AsyncQdrantClient(url=settings.qdrant_url)

        count = await client.count(
            collection_name=settings.qdrant_collection_name,
            exact=True,
        )

        qdrant_vectors = count.count

        print("Vectors")
        print("-" * 65)

        row("Qdrant vectors", qdrant_vectors)

        print()

        print("Consistency")
        print("-" * 65)

        row(
            "Indexed docs without chunks",
            len(indexed_without_chunks),
        )

        row(
            "Chunks without vector id",
            missing_vectors,
        )

        print()

        if indexed_without_chunks:

            ok = False

            print("Documents missing chunks")

            for doc in indexed_without_chunks:
                print(f"  • {doc.original_filename}")

            print()

        if status["failed"]:

            ok = False

            failed = (
                await db.execute(
                    select(
                        DocumentModel.original_filename,
                        DocumentModel.error_message,
                    )
                    .where(DocumentModel.status == "failed")
                    .limit(10)
                )
            ).all()

            print("Failed documents")

            for doc in failed:

                print(
                    f"  • {doc.original_filename}"
                )

            print()

        if missing_vectors:

            ok = False

        #
        # summary
        #

        print("=" * 65)

        if ok:
            print(f"{GREEN} INGESTION HEALTHY")
            return True, "healthy"

        print(f"{RED} INGESTION FAILED")

        return False, "ingestion problems"


if __name__ == "__main__":
    asyncio.run(run())
