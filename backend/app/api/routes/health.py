"""
Health check and application status endpoints.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, Settings
from app.core.database import get_db
from app.models.database_models import Document, Chunk, Conversation, ProcessingStatus
from app.schemas.common import HealthResponse, StatusResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    db: AsyncSession = Depends(get_db),
):
    """
    Health check endpoint.
    Returns service status for all external dependencies.
    """
    settings = get_settings()
    services = {}

    # Check database
    try:
        await db.execute(select(func.count()).select_from(Document))
        services["database"] = {"status": "healthy", "type": "sqlite"}
    except Exception as e:
        services["database"] = {"status": "unhealthy", "error": str(e)}

    # Check Gemini API key configured
    services["gemini"] = {
        "status": "configured" if settings.gemini_api_key else "not_configured",
        "generation_model": settings.gemini_generation_model,
        "embedding_model": settings.gemini_embedding_model,
    }

    # Check Pinecone key configured
    services["pinecone"] = {
        "status": "configured" if settings.pinecone_api_key else "not_configured",
        "index": settings.pinecone_index_name,
    }

    # Check web search
    services["web_search"] = {
        "status": "configured" if settings.web_search_api_key else "not_configured",
        "provider": settings.web_search_provider or "none",
    }

    overall_status = "healthy" if all(
        s.get("status") in ("healthy", "configured", "not_configured")
        for s in services.values()
    ) else "degraded"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        timestamp=datetime.now(timezone.utc),
        services=services,
    )


@router.get("/api/status", response_model=StatusResponse)
async def application_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Application status endpoint.
    Returns real statistics from the database.
    """
    settings = get_settings()

    # Get real counts from database
    doc_count = (await db.execute(
        select(func.count()).select_from(Document).where(
            Document.processing_status != ProcessingStatus.DELETING
        )
    )).scalar() or 0

    chunk_count = (await db.execute(
        select(func.count()).select_from(Chunk)
    )).scalar() or 0

    conv_count = (await db.execute(
        select(func.count()).select_from(Conversation)
    )).scalar() or 0

    return StatusResponse(
        gemini_configured=bool(settings.gemini_api_key),
        gemini_model=settings.gemini_generation_model,
        embedding_model=settings.gemini_embedding_model,
        embedding_dimension=settings.embedding_dimension,
        pinecone_configured=bool(settings.pinecone_api_key),
        pinecone_index=settings.pinecone_index_name,
        web_search_configured=bool(settings.web_search_api_key),
        total_documents=doc_count,
        total_chunks=chunk_count,
        total_conversations=conv_count,
    )
