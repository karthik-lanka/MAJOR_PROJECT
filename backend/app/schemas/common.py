"""
Common Pydantic schemas shared across the application.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = True
    message: str = ""
    data: Optional[Any] = None
    errors: Optional[list[str]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime
    services: dict[str, dict[str, Any]] = {}


class StatusResponse(BaseModel):
    """Application status response."""
    gemini_configured: bool = False
    gemini_model: str = ""
    embedding_model: str = ""
    embedding_dimension: int = 768
    pinecone_configured: bool = False
    pinecone_index: str = ""
    web_search_configured: bool = False
    total_documents: int = 0
    total_chunks: int = 0
    total_conversations: int = 0


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class ErrorDetail(BaseModel):
    """Structured error detail."""
    code: str
    message: str
    field: Optional[str] = None
