"""
Document-related Pydantic schemas.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    """Response schema for a document."""
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    upload_timestamp: datetime
    processing_status: str
    user_id: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: int = 0
    error_message: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    """Response schema for listing documents."""
    documents: list[DocumentResponse]
    total: int


class DocumentStatusResponse(BaseModel):
    """Response schema for document processing status."""
    id: str
    filename: str
    processing_status: str
    page_count: Optional[int] = None
    chunk_count: int = 0
    error_message: Optional[str] = None


class ChunkResponse(BaseModel):
    """Response schema for a document chunk."""
    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    token_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(BaseModel):
    """Detailed document response with chunks."""
    document: DocumentResponse
    chunks: list[ChunkResponse] = []
    total_chunks: int = 0
