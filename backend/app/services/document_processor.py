"""
Document processor service.
Handles the full pipeline: extraction → chunking → embedding → indexing.
Supports PDF, TXT, DOCX, and images.
"""

import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.database_models import Document, Chunk, ProcessingStatus
from app.services.chunking_service import ChunkingService, PageText
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class DocumentProcessorService:
    """Full document processing pipeline."""

    def __init__(self):
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self.settings = get_settings()

    async def process_document(self, document_id: str) -> None:
        """
        Process a document through the full pipeline:
        UPLOADED → EXTRACTING → CHUNKING → EMBEDDING → INDEXING → READY
        """
        async with get_db_session() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if not document:
                logger.error(f"Document not found: {document_id}")
                return

            if not document.storage_path or not Path(document.storage_path).exists():
                await self._set_failed(db, document, "Source file not found on disk")
                return

            try:
                # Phase 1: Extract text
                document.processing_status = ProcessingStatus.EXTRACTING
                document.processing_started_at = datetime.now(timezone.utc)
                await db.commit()

                pages = await self._extract_text(document)

                if not pages:
                    await self._set_failed(
                        db, document, "No text could be extracted from the document"
                    )
                    return

                document.page_count = len(pages)

                # Phase 2: Chunk
                document.processing_status = ProcessingStatus.CHUNKING
                await db.commit()

                chunks = self.chunking_service.chunk_pages(pages)

                if not chunks:
                    await self._set_failed(db, document, "No chunks generated from extracted text")
                    return

                # Phase 3: Embed
                document.processing_status = ProcessingStatus.EMBEDDING
                await db.commit()

                chunk_texts = [c.text for c in chunks]
                embeddings = await self.embedding_service.embed_document_chunks(chunk_texts)

                if len(embeddings) != len(chunks):
                    await self._set_failed(
                        db, document,
                        f"Embedding count mismatch: {len(embeddings)} embeddings for {len(chunks)} chunks",
                    )
                    return

                # Phase 4: Index
                document.processing_status = ProcessingStatus.INDEXING
                await db.commit()

                # Save chunks to database and prepare Pinecone vectors
                vectors = []
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_id = f"{document_id}_chunk_{i:04d}"

                    db_chunk = Chunk(
                        id=chunk_id,
                        document_id=document_id,
                        chunk_index=chunk.chunk_index,
                        chunk_text=chunk.text,
                        page_number=chunk.page_number,
                        page_range_start=chunk.page_range_start,
                        page_range_end=chunk.page_range_end,
                        section_heading=chunk.section_heading,
                        token_count=chunk.token_count,
                        content_hash=chunk.content_hash,
                        embedding_model=self.settings.gemini_embedding_model,
                        embedding_dimension=self.settings.embedding_dimension,
                        pinecone_id=chunk_id,
                    )
                    db.add(db_chunk)

                    vectors.append({
                        "id": chunk_id,
                        "values": embedding,
                        "metadata": {
                            "document_id": document_id,
                            "user_id": document.user_id or "",
                            "chunk_id": chunk_id,
                            "filename": document.original_filename,
                            "file_type": document.file_type,
                            "page_number": chunk.page_number or 0,
                            "page_range_start": chunk.page_range_start or 0,
                            "page_range_end": chunk.page_range_end or 0,
                            "section_heading": chunk.section_heading or "",
                            "chunk_index": chunk.chunk_index,
                            "chunk_text": chunk.text,
                            "content_hash": chunk.content_hash,
                        },
                    })

                # Upsert to Pinecone
                await self.vector_store.upsert_vectors(vectors)

                # Update document status
                document.chunk_count = len(chunks)
                document.processing_status = ProcessingStatus.READY
                document.processing_completed_at = datetime.now(timezone.utc)
                document.error_message = None
                await db.commit()

                logger.info(
                    f"Document processed: {document_id} "
                    f"({len(pages)} pages, {len(chunks)} chunks)"
                )

            except Exception as e:
                logger.error(f"Processing failed for {document_id}: {e}", exc_info=True)
                await self._set_failed(db, document, str(e))

    async def _extract_text(self, document: Document) -> list[PageText]:
        """Extract text from a document based on its file type."""
        file_path = Path(document.storage_path)
        file_type = document.file_type.lower()

        if file_type == "pdf":
            return await self._extract_pdf(file_path)
        elif file_type == "txt":
            return await self._extract_txt(file_path)
        elif file_type == "docx":
            return await self._extract_docx(file_path)
        elif file_type in ("png", "jpg", "jpeg"):
            return await self._extract_image(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    async def _extract_pdf(self, file_path: Path) -> list[PageText]:
        """Extract text from a PDF using PyMuPDF, with OCR fallback for scanned pages."""
        import fitz  # PyMuPDF

        pages = []

        try:
            doc = fitz.open(str(file_path))

            # Fast text extraction pass across all pages
            raw_pages = []
            total_extracted_chars = 0
            for page_num in range(len(doc)):
                page = doc[page_num]
                txt = page.get_text("text").strip()
                raw_pages.append((page_num, page, txt))
                total_extracted_chars += len(txt)

            # Only fallback to heavy OCR if the whole document has basically no extractable text
            is_scanned_pdf = total_extracted_chars < 50

            for page_num, page, clean_text in raw_pages:
                if is_scanned_pdf and len(clean_text) < 50:
                    ocr_text = await self._ocr_page(page)
                    if ocr_text and len(ocr_text.strip()) > len(clean_text):
                        clean_text = ocr_text.strip()

                if clean_text:
                    heading = self._detect_heading(clean_text)
                    pages.append(PageText(
                        text=self._normalize_text(clean_text),
                        page_number=page_num + 1,
                        heading=heading,
                    ))

            doc.close()

        except Exception as e:
            logger.error(f"PDF extraction failed for {file_path}: {e}")
            raise

        return pages

    async def _extract_txt(self, file_path: Path) -> list[PageText]:
        """Extract text from a plain text file."""
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                return []
            return [PageText(
                text=self._normalize_text(text),
                page_number=1,
            )]
        except Exception as e:
            logger.error(f"TXT extraction failed for {file_path}: {e}")
            raise

    async def _extract_docx(self, file_path: Path) -> list[PageText]:
        """Extract text from a DOCX file."""
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(str(file_path))
            pages = []
            current_text = ""
            current_heading = None
            page_num = 1

            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue

                # Detect headings from paragraph style
                if paragraph.style and paragraph.style.name and "heading" in paragraph.style.name.lower():
                    # Flush current page
                    if current_text:
                        pages.append(PageText(
                            text=self._normalize_text(current_text),
                            page_number=page_num,
                            heading=current_heading,
                        ))
                        page_num += 1
                        current_text = ""
                    current_heading = text
                    current_text = text + "\n\n"
                else:
                    current_text += text + "\n"

            # Add remaining text
            if current_text.strip():
                pages.append(PageText(
                    text=self._normalize_text(current_text),
                    page_number=page_num,
                    heading=current_heading,
                ))

            # Also extract tables
            for i, table in enumerate(doc.tables):
                table_text = self._extract_docx_table(table)
                if table_text:
                    pages.append(PageText(
                        text=table_text,
                        page_number=page_num + 1 + i,
                        heading=f"Table {i + 1}",
                    ))

            return pages

        except Exception as e:
            logger.error(f"DOCX extraction failed for {file_path}: {e}")
            raise

    async def _extract_image(self, file_path: Path) -> list[PageText]:
        """Extract text from an image using OCR."""
        try:
            text = await self._ocr_image_file(file_path)
            if not text or not text.strip():
                # Try Gemini vision as fallback
                text = await self._vision_extract(file_path)

            if text and text.strip():
                return [PageText(
                    text=self._normalize_text(text),
                    page_number=1,
                    heading=f"Image: {file_path.name}",
                )]
            else:
                logger.warning(f"No text extracted from image: {file_path}")
                return []

        except Exception as e:
            logger.error(f"Image extraction failed for {file_path}: {e}")
            raise

    async def _ocr_page(self, page) -> Optional[str]:
        """OCR a PDF page by rendering it as an image."""
        try:
            import io
            from PIL import Image

            # Render page as image
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # Try pytesseract
            try:
                import pytesseract
                text = pytesseract.image_to_string(img)
                if text and len(text.strip()) > 20:
                    return text
            except Exception:
                pass

            # Fallback to Gemini vision
            return await self._vision_extract_image(img)

        except Exception as e:
            logger.warning(f"OCR failed for page: {e}")
            return None

    async def _ocr_image_file(self, file_path: Path) -> Optional[str]:
        """OCR a standalone image file."""
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(str(file_path))
            text = pytesseract.image_to_string(img)
            return text if text and text.strip() else None
        except ImportError:
            logger.warning("pytesseract not available for OCR")
            return None
        except Exception as e:
            logger.warning(f"OCR failed for {file_path}: {e}")
            return None

    async def _vision_extract(self, file_path: Path) -> Optional[str]:
        """Use Gemini vision to extract text from an image file."""
        try:
            import asyncio
            from google import genai
            from google.genai import types

            settings = get_settings()
            client = genai.Client(api_key=settings.gemini_api_key)

            # Read the image file
            img_bytes = file_path.read_bytes()
            mime_type = "image/png" if file_path.suffix.lower() == ".png" else "image/jpeg"

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_generation_model,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                    "Read and transcribe all textual content, headings, formulas, and notes from this image verbatim into clean readable text. Do not return JSON coordinates, bounding boxes, or metadata. Output only the transcribed text.",
                ],
            )

            return response.text if response.text else None

        except Exception as e:
            logger.warning(f"Vision extraction failed for {file_path}: {e}")
            return None

    async def _vision_extract_image(self, img) -> Optional[str]:
        """Use Gemini vision to extract text from a PIL Image."""
        try:
            import asyncio
            import io
            from google import genai
            from google.genai import types

            settings = get_settings()
            client = genai.Client(api_key=settings.gemini_api_key)

            # Convert PIL Image to bytes
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_bytes = buffer.getvalue()

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_generation_model,
                contents=[
                    types.Part.from_bytes(data=img_bytes, mime_type="image/png"),
                    "Read and transcribe all textual content visible in this image verbatim into clean readable text. Output only the transcribed text without bounding boxes or JSON.",
                ],
            )

            return response.text if response.text else None

        except Exception as e:
            logger.warning(f"Vision extraction failed: {e}")
            return None

    def _extract_docx_table(self, table) -> Optional[str]:
        """Convert a DOCX table to structured text."""
        try:
            rows = []
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                rows.append(cells)

            if not rows:
                return None

            # Build markdown table
            headers = rows[0]
            md_lines = []
            md_lines.append("| " + " | ".join(headers) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

            for row in rows[1:]:
                # Pad row if needed
                while len(row) < len(headers):
                    row.append("")
                md_lines.append("| " + " | ".join(row[:len(headers)]) + " |")

            return "\n".join(md_lines)

        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
            return None

    def _normalize_text(self, text: str) -> str:
        """Conservative text normalization."""
        # Normalize whitespace (but preserve paragraph breaks)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove common header/footer artifacts
        # Only remove if they appear on multiple "pages" (conservative)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip page numbers alone on a line
            if re.match(r'^\d{1,4}$', stripped):
                continue
            # Skip very short repeated lines that look like headers/footers
            if len(stripped) < 3 and not stripped.isalpha():
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines).strip()

    def _detect_heading(self, text: str) -> Optional[str]:
        """Try to detect the first heading in a text block."""
        first_line = text.split('\n')[0].strip()

        # Check for common heading patterns
        if len(first_line) < 100 and (
            first_line.isupper()
            or re.match(r'^(Chapter|Section|Part|\d+\.)\s', first_line)
            or re.match(r'^#{1,6}\s', first_line)
        ):
            return first_line[:200]

        return None

    async def _set_failed(
        self, db, document: Document, error: str
    ) -> None:
        """Mark a document as failed with an error message."""
        document.processing_status = ProcessingStatus.FAILED
        document.error_message = error[:2000]
        document.processing_completed_at = datetime.now(timezone.utc)
        await db.commit()
        logger.error(f"Document {document.id} failed: {error}")
