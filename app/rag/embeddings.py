"""
Embedding generation service.
Wraps OpenAI embeddings with batching, retry logic, and caching.
"""
import asyncio
import hashlib
import json
from typing import Any

import redis.asyncio as aioredis
from langchain_ollama import OllamaEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger
import httpx

logger = get_logger(__name__)

# Batch limits for OpenAI embeddings API
OPENAI_EMBEDDING_BATCH_SIZE = 100


class EmbeddingService:
    """
    Production embedding service with:
    - Batched API calls
    - Redis caching
    - Exponential backoff retries
    - Token usage tracking
    """

    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,  # type: ignore[type-arg]
    ) -> None:
        self._settings = get_settings()
        self._redis = redis_client
        self._embeddings = OllamaEmbeddings(
            model="nomic-embed-text",
            base_url=self._settings.ollama_base_url,
        )
        self._base_url = self._settings.ollama_base_url
        self._model = self._settings.ollama_embedding_model
        self._dimensions = self._settings.ollama_embedding_dimensions
        logger.warning(
            "OLLAMA_CONFIG",
            base_url=self._settings.ollama_base_url,
            llm_model=self._settings.ollama_model,
            embedding_model=self._settings.ollama_embedding_model,
        )

    async def embed_text(self, text: str) -> list[float]:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self._settings.ollama_base_url}/api/embed",
                json={
                    "model": self._model,
                    "input": text,
                },
            )
        print('self._model in embed_text = ',self._model)
        response.raise_for_status()

        data = response.json()
        print('data["embeddings"]')
        print(data)
        embeddings = data["embeddings"]

        if not embeddings:
            raise ValueError("No embeddings returned")

        return embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a batch of texts.
        Automatically splits into sub-batches and merges results.
        """
        if not texts:
            return []

        # Check cache first
        embeddings: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        if self._redis:
            for i, text in enumerate(texts):
                cached = await self._get_cached_embedding(text)
                if cached is not None:
                    embeddings[i] = cached
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(text)
        else:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        print("INPUT TEXTS:", len(texts))
        print("OUTPUT EMBEDDINGS:", len(embeddings))


        # Process uncached texts in batches
        if uncached_texts:
            new_embeddings = await self._embed_in_batches(uncached_texts)

            for idx, embedding in zip(uncached_indices, new_embeddings):
                embeddings[idx] = embedding

            # Cache the new embeddings
            if self._redis:
                for text, embedding in zip(uncached_texts, new_embeddings):
                    await self._cache_embedding(text, embedding)
        print("OUTPUT new_embeddings:", len(new_embeddings))
        print("OUTPUT embeddings2:", len(embeddings))
        return [e for e in embeddings if e is not None]

    async def _embed_in_batches(self, texts: list[str]) -> list[list[float]]:
        """Process texts in batches respecting API limits."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), OPENAI_EMBEDDING_BATCH_SIZE):
            batch = texts[i: i + OPENAI_EMBEDDING_BATCH_SIZE]
            batch_embeddings = await self._call_ollama_embedding(batch)
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to be rate-limit friendly
            if i + OPENAI_EMBEDDING_BATCH_SIZE < len(texts):
                await asyncio.sleep(0.1)

        return all_embeddings

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def _call_ollama_embedding(
            self,
            texts: list[str]
    ) -> list[list[float]]:

        embeddings = []

        async with httpx.AsyncClient(timeout=120) as client:
            for text in texts:
                response = await client.post(
                    f"{self._base_url}/api/embed",
                    json={
                        "model": self._model,
                        "input": text,
                    },
                )

                response.raise_for_status()

                data = response.json()

                embeddings.extend(data["embeddings"])

        return embeddings

    # -------------------------------------------------------------------------
    # Cache helpers
    # -------------------------------------------------------------------------

    def _cache_key(self, text: str) -> str:
        """Generate a deterministic cache key for a text."""
        hash_val = hashlib.sha256(
            f"{self._model}:{self._dimensions}:{text}".encode()
        ).hexdigest()[:16]
        return f"embedding:{hash_val}"

    async def _get_cached_embedding(self, text: str) -> list[float] | None:
        """Retrieve embedding from Redis cache."""
        if not self._redis:
            return None
        try:
            key = self._cache_key(text)
            cached = await self._redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(
                "_get_cached_embedding",
                error=str(e),
                error_type=type(e).__name__,
            )
            import traceback
            traceback.print_exc()
            raise
        return None

    async def _cache_embedding(self, text: str, embedding: list[float]) -> None:
        """Store embedding in Redis cache with TTL."""
        if not self._redis:
            return
        try:
            key = self._cache_key(text)
            await self._redis.setex(
                key,
                self._settings.redis_cache_ttl,
                json.dumps(embedding),
            )
        except Exception as e:
            logger.error(
                "embedding_cache_write_failed",
                error=str(e),
                error_type=type(e).__name__,
            )

