"""
Retrieval service for semantic search over indexed documents.
"""

import logging
from typing import Optional
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A retrieved chunk with score and metadata."""
    chunk_id: str
    document_id: str
    text: str
    score: float
    page_number: Optional[int] = None
    page_range_start: Optional[int] = None
    page_range_end: Optional[int] = None
    filename: Optional[str] = None
    section_heading: Optional[str] = None
    chunk_index: int = 0


class RetrievalService:
    """Semantic retrieval over indexed document chunks."""

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self.settings = get_settings()

    async def retrieve(
        self,
        query: str,
        document_ids: Optional[list[str]] = None,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks for a query.

        1. Embed the query using RETRIEVAL_QUERY task type
        2. Search Pinecone with optional document filters
        3. Filter by similarity threshold
        4. Return ranked chunks
        """
        top_k = top_k or self.settings.retrieval_top_k
        threshold = similarity_threshold or self.settings.similarity_threshold

        # Embed the query
        query_vector = await self.embedding_service.embed_query(query)

        # Build filter
        filter_dict = None
        if document_ids:
            if len(document_ids) == 1:
                filter_dict = {"document_id": {"$eq": document_ids[0]}}
            else:
                filter_dict = {"document_id": {"$in": document_ids}}

        # Search Pinecone
        matches = await self.vector_store.query(
            vector=query_vector,
            top_k=top_k,
            filter_dict=filter_dict,
            include_metadata=True,
        )

        # Convert to RetrievedChunk objects and filter by threshold
        chunks = []
        for match in matches:
            if match["score"] < threshold:
                continue

            metadata = match.get("metadata", {})
            chunks.append(RetrievedChunk(
                chunk_id=match["id"],
                document_id=metadata.get("document_id", ""),
                text=metadata.get("chunk_text", ""),
                score=match["score"],
                page_number=metadata.get("page_number"),
                page_range_start=metadata.get("page_range_start"),
                page_range_end=metadata.get("page_range_end"),
                filename=metadata.get("filename"),
                section_heading=metadata.get("section_heading"),
                chunk_index=metadata.get("chunk_index", 0),
            ))

        logger.info(
            f"Retrieved {len(chunks)} chunks for query "
            f"(threshold={threshold}, top_k={top_k})"
        )

        return chunks

    async def retrieve_for_context(
        self,
        query: str,
        document_ids: Optional[list[str]] = None,
        max_context_chunks: Optional[int] = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve chunks and select the best ones for context.
        Returns at most max_context_chunks results.
        """
        max_chunks = max_context_chunks or self.settings.final_context_top_k

        # Retrieve more candidates than we need
        candidates = await self.retrieve(
            query=query,
            document_ids=document_ids,
            top_k=self.settings.retrieval_top_k,
        )

        # Return top chunks (already sorted by score from Pinecone)
        return candidates[:max_chunks]
