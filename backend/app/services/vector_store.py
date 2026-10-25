"""
Vector store service using Pinecone.
Handles index management, upsert, query, and deletion.
"""

import asyncio
import logging
from typing import Optional

from pinecone import Pinecone, ServerlessSpec

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Manage vector storage and retrieval with Pinecone."""

    def __init__(self):
        settings = get_settings()
        self.pc = Pinecone(api_key=settings.pinecone_api_key)
        self.index_name = settings.pinecone_index_name
        self.namespace = settings.pinecone_namespace
        self.dimension = settings.embedding_dimension
        self._index = None

    def _get_index(self):
        """Get or create the Pinecone index."""
        if self._index is not None:
            return self._index

        # Check if index exists
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name} (dim={self.dimension})")
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info(f"Pinecone index created: {self.index_name}")

        self._index = self.pc.Index(self.index_name)
        return self._index

    async def upsert_vectors(
        self,
        vectors: list[dict],
    ) -> int:
        """
        Upsert vectors to Pinecone.

        Args:
            vectors: List of dicts with 'id', 'values', and 'metadata' keys.

        Returns:
            Number of vectors upserted.
        """
        if not vectors:
            return 0

        index = await asyncio.to_thread(self._get_index)

        # Batch upsert (Pinecone recommends batches of 100)
        batch_size = 100
        total_upserted = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]

            # Prepare records for Pinecone
            records = []
            for v in batch:
                # Truncate metadata values to stay within limits
                metadata = self._sanitize_metadata(v.get("metadata", {}))
                records.append({
                    "id": v["id"],
                    "values": v["values"],
                    "metadata": metadata,
                })

            try:
                await asyncio.to_thread(
                    index.upsert,
                    vectors=records,
                    namespace=self.namespace,
                )
                total_upserted += len(records)
            except Exception as e:
                logger.error(f"Pinecone upsert failed (batch {i // batch_size}): {e}")
                raise

            # Rate limiting between batches
            if i + batch_size < len(vectors):
                await asyncio.sleep(0.2)

        logger.info(f"Upserted {total_upserted} vectors to Pinecone")
        return total_upserted

    async def query(
        self,
        vector: list[float],
        top_k: int = 10,
        filter_dict: Optional[dict] = None,
        include_metadata: bool = True,
    ) -> list[dict]:
        """
        Query Pinecone for similar vectors.

        Returns list of matches with id, score, and metadata.
        """
        index = await asyncio.to_thread(self._get_index)

        try:
            result = await asyncio.to_thread(
                index.query,
                vector=vector,
                top_k=top_k,
                namespace=self.namespace,
                filter=filter_dict,
                include_metadata=include_metadata,
            )

            matches = []
            for match in result.get("matches", []):
                matches.append({
                    "id": match["id"],
                    "score": match["score"],
                    "metadata": match.get("metadata", {}),
                })

            return matches

        except Exception as e:
            logger.error(f"Pinecone query failed: {e}")
            raise

    async def delete_document_vectors(self, document_id: str) -> None:
        """Delete all vectors associated with a document."""
        index = await asyncio.to_thread(self._get_index)

        try:
            # Use metadata filter to find and delete vectors
            # First, query for all vector IDs belonging to this document
            # Pinecone supports deleting by filter in some tiers
            await asyncio.to_thread(
                index.delete,
                filter={"document_id": {"$eq": document_id}},
                namespace=self.namespace,
            )
            logger.info(f"Deleted vectors for document: {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete vectors for document {document_id}: {e}")
            raise

    async def delete_vectors_by_ids(self, vector_ids: list[str]) -> None:
        """Delete specific vectors by their IDs."""
        if not vector_ids:
            return

        index = await asyncio.to_thread(self._get_index)

        try:
            await asyncio.to_thread(
                index.delete,
                ids=vector_ids,
                namespace=self.namespace,
            )
            logger.info(f"Deleted {len(vector_ids)} vectors")
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}")
            raise

    async def get_index_stats(self) -> dict:
        """Get index statistics."""
        try:
            index = await asyncio.to_thread(self._get_index)
            stats = await asyncio.to_thread(index.describe_index_stats)
            return {
                "total_vector_count": stats.get("total_vector_count", 0),
                "dimension": stats.get("dimension", self.dimension),
                "namespaces": stats.get("namespaces", {}),
            }
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}

    def _sanitize_metadata(self, metadata: dict) -> dict:
        """
        Sanitize metadata to stay within Pinecone limits.
        Pinecone metadata limit is ~40KB per vector.
        Truncate long text fields.
        """
        sanitized = {}
        max_text_length = 8000  # Keep well under 40KB limit

        for key, value in metadata.items():
            if isinstance(value, str):
                sanitized[key] = value[:max_text_length]
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif isinstance(value, list):
                sanitized[key] = [
                    str(v)[:500] for v in value[:20]
                ]
            else:
                sanitized[key] = str(value)[:max_text_length]

        return sanitized

    async def health_check(self) -> dict:
        """Check if Pinecone is accessible."""
        try:
            stats = await self.get_index_stats()
            if "error" in stats:
                return {"status": "unhealthy", "error": stats["error"]}
            return {
                "status": "healthy",
                "index": self.index_name,
                "total_vectors": stats.get("total_vector_count", 0),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
