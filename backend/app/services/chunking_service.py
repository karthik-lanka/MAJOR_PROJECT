"""
Chunking service for splitting extracted text into indexable chunks.
Supports semantic-aware splitting with configurable size and overlap.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    text: str
    chunk_index: int
    page_number: Optional[int] = None
    page_range_start: Optional[int] = None
    page_range_end: Optional[int] = None
    section_heading: Optional[str] = None
    token_count: int = 0
    content_hash: str = ""


@dataclass
class PageText:
    """Text extracted from a single page."""
    text: str
    page_number: int
    heading: Optional[str] = None


class ChunkingService:
    """Split document text into chunks suitable for embedding and retrieval."""

    def __init__(self):
        settings = get_settings()
        self.chunk_size = settings.chunk_size_tokens
        self.chunk_overlap = settings.chunk_overlap_tokens
        self._avg_chars_per_token = 4  # Approximate for English text

    def chunk_pages(self, pages: list[PageText]) -> list[TextChunk]:
        """
        Chunk a list of page texts into overlapping chunks.
        Respects page boundaries where possible and preserves headings.
        """
        if not pages:
            return []

        # Combine pages into segments with metadata
        segments = self._extract_segments(pages)

        # Split segments into chunks
        chunks = self._split_into_chunks(segments)

        # Deduplicate
        seen_hashes = set()
        unique_chunks = []
        for chunk in chunks:
            if chunk.content_hash not in seen_hashes:
                seen_hashes.add(chunk.content_hash)
                unique_chunks.append(chunk)

        logger.info(f"Created {len(unique_chunks)} chunks from {len(pages)} pages")
        return unique_chunks

    def chunk_text(self, text: str, source_page: Optional[int] = None) -> list[TextChunk]:
        """Chunk a single text string."""
        pages = [PageText(text=text, page_number=source_page or 1)]
        return self.chunk_pages(pages)

    def _extract_segments(self, pages: list[PageText]) -> list[dict]:
        """
        Extract text segments from pages.
        Tries to split at headings and paragraph boundaries.
        """
        segments = []

        for page in pages:
            text = page.text.strip()
            if not text:
                continue

            # Try to detect headings in the text
            heading_pattern = re.compile(
                r'^(?:#{1,6}\s+|(?:Chapter|Section|Part)\s+\d+[.:]\s*|'
                r'\d+\.\d*\s+[A-Z]|\b[A-Z][A-Z\s]{3,}(?:\n|$))',
                re.MULTILINE,
            )

            # Split by headings
            parts = heading_pattern.split(text)
            headings = heading_pattern.findall(text)

            if len(headings) > 0 and len(parts) > 1:
                current_heading = page.heading
                for i, part in enumerate(parts):
                    if part.strip():
                        if i > 0 and i - 1 < len(headings):
                            current_heading = headings[i - 1].strip().rstrip(":.")
                        segments.append({
                            "text": part.strip(),
                            "page": page.page_number,
                            "heading": current_heading,
                        })
            else:
                # Split by paragraphs for long pages
                paragraphs = re.split(r'\n\s*\n', text)
                for para in paragraphs:
                    if para.strip():
                        segments.append({
                            "text": para.strip(),
                            "page": page.page_number,
                            "heading": page.heading,
                        })

        return segments

    def _split_into_chunks(self, segments: list[dict]) -> list[TextChunk]:
        """
        Split segments into chunks of approximately chunk_size tokens.
        Uses overlap to maintain context between chunks.
        """
        chunks = []
        current_text = ""
        current_pages = []
        current_heading = None
        chunk_index = 0

        target_chars = self.chunk_size * self._avg_chars_per_token
        overlap_chars = self.chunk_overlap * self._avg_chars_per_token

        for segment in segments:
            seg_text = segment["text"]
            seg_page = segment["page"]
            seg_heading = segment.get("heading")

            if seg_heading:
                current_heading = seg_heading

            # If adding this segment would exceed the limit
            if current_text and len(current_text) + len(seg_text) > target_chars:
                # Flush current chunk
                chunk = self._create_chunk(
                    current_text, chunk_index, current_pages, current_heading
                )
                chunks.append(chunk)
                chunk_index += 1

                # Keep overlap from the end of current text
                if overlap_chars > 0 and len(current_text) > overlap_chars:
                    # Find a sentence boundary near the overlap point
                    overlap_text = current_text[-overlap_chars:]
                    sentence_start = overlap_text.find(". ")
                    if sentence_start >= 0:
                        overlap_text = overlap_text[sentence_start + 2:]
                    current_text = overlap_text
                    current_pages = [seg_page]
                else:
                    current_text = ""
                    current_pages = []

            # Add segment text
            if current_text:
                current_text += "\n\n" + seg_text
            else:
                current_text = seg_text

            if seg_page not in current_pages:
                current_pages.append(seg_page)

        # Don't forget the last chunk
        if current_text.strip():
            chunk = self._create_chunk(
                current_text, chunk_index, current_pages, current_heading
            )
            chunks.append(chunk)

        # If text was very long and produced a chunk over size, split further
        final_chunks = []
        for chunk in chunks:
            if len(chunk.text) > target_chars * 1.5:
                sub_chunks = self._force_split(chunk, target_chars, overlap_chars)
                for i, sc in enumerate(sub_chunks):
                    sc.chunk_index = len(final_chunks)
                    final_chunks.append(sc)
            else:
                chunk.chunk_index = len(final_chunks)
                final_chunks.append(chunk)

        return final_chunks

    def _create_chunk(
        self,
        text: str,
        index: int,
        pages: list[int],
        heading: Optional[str],
    ) -> TextChunk:
        """Create a TextChunk with computed metadata."""
        text = text.strip()
        content_hash = hashlib.md5(text.encode()).hexdigest()
        token_count = len(text) // self._avg_chars_per_token

        return TextChunk(
            text=text,
            chunk_index=index,
            page_number=pages[0] if pages else None,
            page_range_start=min(pages) if pages else None,
            page_range_end=max(pages) if pages else None,
            section_heading=heading,
            token_count=token_count,
            content_hash=content_hash,
        )

    def _force_split(
        self, chunk: TextChunk, target_chars: int, overlap_chars: int
    ) -> list[TextChunk]:
        """Force-split an oversized chunk at sentence boundaries."""
        text = chunk.text
        sub_chunks = []
        start = 0

        while start < len(text):
            end = min(start + target_chars, len(text))

            # Try to split at sentence boundary
            if end < len(text):
                # Look for sentence end near the target
                search_region = text[max(end - 200, start):end]
                last_period = search_region.rfind(". ")
                if last_period >= 0:
                    end = max(end - 200, start) + last_period + 2

            sub_text = text[start:end].strip()
            if sub_text:
                sub_chunk = TextChunk(
                    text=sub_text,
                    chunk_index=0,
                    page_number=chunk.page_number,
                    page_range_start=chunk.page_range_start,
                    page_range_end=chunk.page_range_end,
                    section_heading=chunk.section_heading,
                    token_count=len(sub_text) // self._avg_chars_per_token,
                    content_hash=hashlib.md5(sub_text.encode()).hexdigest(),
                )
                sub_chunks.append(sub_chunk)

            start = max(start + 1, end - overlap_chars)

        return sub_chunks
