"""
Embedding service using Google Gemini embedding model.
Handles embedding generation for both documents and queries.
"""

import asyncio
import logging
import math
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using Gemini embedding model."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_embedding_model
        self.dimension = settings.embedding_dimension
        self._batch_size = 50  # Fast batch size for rapid vector indexing

    async def embed_document_chunks(
        self, texts: list[str], titles: Optional[list[str]] = None
    ) -> list[list[float]]:
        """
        Generate embeddings for document chunks.
        Uses RETRIEVAL_DOCUMENT task type.
        Batches requests to respect API limits with automatic rate limit backoff.
        """
        if not texts:
            return []

        all_embeddings = []

        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            batch_titles = titles[i : i + self._batch_size] if titles else None

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    result = await asyncio.to_thread(
                        self._embed_batch,
                        batch,
                        "RETRIEVAL_DOCUMENT",
                        batch_titles,
                    )
                    all_embeddings.extend(result)

                    # Minimal delay between batches
                    if i + self._batch_size < len(texts):
                        await asyncio.sleep(0.2)
                    break

                except Exception as e:
                    err_msg = str(e)
                    is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower()
                    
                    if is_rate_limit and attempt < max_retries - 1:
                        # Extract suggested retry delay or use 25s backoff
                        wait_seconds = 25.0 + (attempt * 5.0)
                        logger.warning(
                            f"Gemini embedding quota reached on batch {i // self._batch_size + 1}/{(len(texts) + self._batch_size - 1) // self._batch_size}. "
                            f"Waiting {wait_seconds:.1f}s before retry (attempt {attempt + 1}/{max_retries})..."
                        )
                        await asyncio.sleep(wait_seconds)
                    else:
                        logger.error(f"Embedding batch failed (batch {i // self._batch_size}): {e}")
                        raise

        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate embedding for a search query.
        Uses RETRIEVAL_QUERY task type.
        """
        try:
            result = await asyncio.to_thread(
                self._embed_batch,
                [query],
                "RETRIEVAL_QUERY",
                None,
            )
            return result[0]
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            raise

    def _embed_batch(
        self,
        texts: list[str],
        task_type: str,
        titles: Optional[list[str]] = None,
    ) -> list[list[float]]:
        """Synchronous batch embedding call."""
        config = types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=self.dimension,
        )
        if titles:
            config.title = titles[0] if len(titles) == 1 else None

        result = self.client.models.embed_content(
            model=self.model,
            contents=texts,
            config=config,
        )

        embeddings = []
        for embedding in result.embeddings:
            vector = list(embedding.values)

            # Validate vector
            if len(vector) != self.dimension:
                logger.warning(
                    f"Unexpected embedding dimension: {len(vector)} (expected {self.dimension})"
                )

            if any(math.isnan(v) or math.isinf(v) for v in vector):
                raise ValueError("Embedding contains NaN or Inf values")

            embeddings.append(vector)

        return embeddings

    async def health_check(self) -> dict:
        """Check if the embedding service is working."""
        try:
            result = await self.embed_query("health check test")
            return {
                "status": "healthy",
                "model": self.model,
                "dimension": len(result),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
