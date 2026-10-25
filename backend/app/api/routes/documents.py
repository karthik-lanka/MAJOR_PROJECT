"""
Document management API routes.
Upload, list, get, delete, and reprocess documents.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.models.database_models import Document, Chunk, ProcessingStatus
from app.schemas.common import APIResponse
from app.schemas.documents import (
    DocumentResponse,
    DocumentListResponse,
    DocumentStatusResponse,
    DocumentDetailResponse,
    ChunkResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

# Allowed file extensions and MIME types
ALLOWED_EXTENSIONS = {
    ".pdf": ["application/pdf"],
    ".txt": ["text/plain"],
    ".docx": [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ],
    ".png": ["image/png"],
    ".jpg": ["image/jpeg"],
    ".jpeg": ["image/jpeg"],
}

FILE_SIGNATURES = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG"],
    ".jpg": [b"\xff\xd8\xff"],
    ".jpeg": [b"\xff\xd8\xff"],
    ".docx": [b"PK\x03\x04"],
}


def validate_file(file: UploadFile, max_size_bytes: int) -> tuple[str, str]:
    """
    Validate an uploaded file.
    Returns (extension, sanitized_filename).
    Raises HTTPException on validation failure.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Get and validate extension
    filename = file.filename.strip()
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(ALLOWED_EXTENSIONS.keys())}",
        )

    # Validate MIME type
    if file.content_type:
        allowed_mimes = ALLOWED_EXTENSIONS[ext]
        # Be lenient with MIME type checking (browsers may report differently)
        if file.content_type not in allowed_mimes and file.content_type != "application/octet-stream":
            logger.warning(
                f"MIME type mismatch for {filename}: expected {allowed_mimes}, got {file.content_type}"
            )

    # Sanitize filename (prevent path traversal)
    sanitized = Path(filename).name  # Strip any directory components
    sanitized = "".join(
        c if c.isalnum() or c in ".-_ " else "_" for c in sanitized
    )

    return ext, sanitized


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document for processing.
    The document is saved, validated, and processing begins in the background.
    """
    settings = get_settings()

    # Validate file
    ext, sanitized_filename = validate_file(file, settings.max_upload_size_bytes)

    # Read file content
    content = await file.read()

    # Check file size
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size ({len(content) / 1024 / 1024:.1f}MB) exceeds maximum ({settings.max_upload_size_mb}MB)",
        )

    # Validate file signature (magic bytes)
    if ext in FILE_SIGNATURES:
        valid_sigs = FILE_SIGNATURES[ext]
        if not any(content.startswith(sig) for sig in valid_sigs):
            raise HTTPException(
                status_code=400,
                detail=f"File content does not match expected format for '{ext}'",
            )

    # Generate content hash for deduplication
    content_hash = hashlib.sha256(content).hexdigest()

    # Generate unique storage filename
    doc_id = str(uuid.uuid4())
    storage_filename = f"{doc_id}{ext}"

    # Save file to disk
    upload_dir = settings.upload_dir
    storage_path = upload_dir / storage_filename

    with open(storage_path, "wb") as f:
        f.write(content)

    # Create database record
    document = Document(
        id=doc_id,
        filename=storage_filename,
        original_filename=sanitized_filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        user_id=user_id,
        processing_status=ProcessingStatus.UPLOADED,
        content_hash=content_hash,
        storage_path=str(storage_path),
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(f"Document uploaded: {doc_id} ({sanitized_filename}, {len(content)} bytes, user: {user_id})")

    # Start background processing
    background_tasks.add_task(process_document_task, doc_id)

    return DocumentResponse.model_validate(document)


async def process_document_task(document_id: str) -> None:
    """Background task to process an uploaded document through the full pipeline."""
    from app.services.document_processor import DocumentProcessorService

    logger.info(f"Starting document processing: {document_id}")
    try:
        processor = DocumentProcessorService()
        await processor.process_document(document_id)
        logger.info(f"Document processing completed: {document_id}")
    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}", exc_info=True)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List documents for the authenticated user, including any unassigned documents."""
    if user_id:
        # Adopt any unassigned documents for this user so they are preserved
        unassigned_result = await db.execute(
            select(Document).where(
                Document.user_id.is_(None),
                Document.processing_status != ProcessingStatus.DELETING,
            )
        )
        unassigned_docs = unassigned_result.scalars().all()
        if unassigned_docs:
            for d in unassigned_docs:
                d.user_id = user_id
            await db.commit()

        result = await db.execute(
            select(Document)
            .where(
                Document.processing_status != ProcessingStatus.DELETING,
                Document.user_id == user_id,
            )
            .order_by(Document.upload_timestamp.desc())
        )
    else:
        # Return unassigned documents for guest session
        result = await db.execute(
            select(Document)
            .where(
                Document.processing_status != ProcessingStatus.DELETING,
                Document.user_id.is_(None),
            )
            .order_by(Document.upload_timestamp.desc())
        )

    documents = result.scalars().all()

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(doc) for doc in documents],
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a specific document including its chunks."""
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.chunks))
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = sorted(document.chunks, key=lambda c: c.chunk_index)

    return DocumentDetailResponse(
        document=DocumentResponse.model_validate(document),
        chunks=[ChunkResponse.model_validate(c) for c in chunks],
        total_chunks=len(chunks),
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the processing status of a document."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentStatusResponse(
        id=document.id,
        filename=document.original_filename,
        processing_status=document.processing_status.value,
        page_count=document.page_count,
        chunk_count=document.chunk_count,
        error_message=document.error_message,
    )


@router.post("/{document_id}/reprocess", response_model=APIResponse)
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Reprocess a document (re-extract, re-chunk, re-embed)."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.processing_status == ProcessingStatus.DELETING:
        raise HTTPException(status_code=400, detail="Document is being deleted")

    # Delete existing chunks
    await db.execute(
        sa_delete(Chunk).where(Chunk.document_id == document_id)
    )

    # Reset status
    document.processing_status = ProcessingStatus.UPLOADED
    document.chunk_count = 0
    document.error_message = None
    document.processing_started_at = None
    document.processing_completed_at = None

    await db.commit()

    # Start reprocessing
    background_tasks.add_task(process_document_task, document_id)

    return APIResponse(
        success=True,
        message=f"Reprocessing started for document '{document.original_filename}'",
    )


@router.delete("/{document_id}", response_model=APIResponse)
async def delete_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a document and all associated data.
    Removes: file from disk, chunks from database, vectors from Pinecone.
    """
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Mark as deleting
    document.processing_status = ProcessingStatus.DELETING
    await db.commit()

    # Delete in background (Pinecone vectors, file, then DB record)
    background_tasks.add_task(delete_document_task, document_id)

    return APIResponse(
        success=True,
        message=f"Document '{document.original_filename}' is being deleted",
    )


async def delete_document_task(document_id: str) -> None:
    """Background task to fully delete a document and its associated resources."""
    from app.core.database import get_db_session

    logger.info(f"Starting document deletion: {document_id}")

    try:
        # Delete from Pinecone
        try:
            from app.services.vector_store import VectorStoreService
            vector_store = VectorStoreService()
            await vector_store.delete_document_vectors(document_id)
            logger.info(f"Pinecone vectors deleted for document: {document_id}")
        except Exception as e:
            logger.error(f"Failed to delete Pinecone vectors for {document_id}: {e}")

        async with get_db_session() as db:
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()

            if document:
                # Delete file from disk
                if document.storage_path:
                    storage_path = Path(document.storage_path)
                    if storage_path.exists():
                        storage_path.unlink()
                        logger.info(f"File deleted from disk: {storage_path}")

                # Delete DB record (cascades to chunks)
                await db.delete(document)
                await db.commit()
                logger.info(f"Document deleted from database: {document_id}")

    except Exception as e:
        logger.error(f"Document deletion failed for {document_id}: {e}", exc_info=True)
