"""
Study assistance API routes.
Summaries, explanations, revision notes, and practice questions.
"""

import logging
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.study import (
    SummarizeRequest,
    ExplainRequest,
    RevisionNotesRequest,
    PracticeQuestionsRequest,
    StudyContentResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/study", tags=["Study"])


@router.post("/summarize", response_model=StudyContentResponse)
async def summarize_document(
    request: SummarizeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a summary of selected documents or sections."""
    start_time = time.time()

    try:
        from app.services.study_service import StudyService

        study_service = StudyService(db)
        result = await study_service.summarize(request)
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate summary")


@router.post("/explain", response_model=StudyContentResponse)
async def explain_concept(
    request: ExplainRequest,
    db: AsyncSession = Depends(get_db),
):
    """Explain a concept using relevant uploaded materials."""
    start_time = time.time()

    try:
        from app.services.study_service import StudyService

        study_service = StudyService(db)
        result = await study_service.explain(request)
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Explanation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate explanation")


@router.post("/revision-notes", response_model=StudyContentResponse)
async def generate_revision_notes(
    request: RevisionNotesRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate revision notes from selected documents."""
    start_time = time.time()

    try:
        from app.services.study_service import StudyService

        study_service = StudyService(db)
        result = await study_service.revision_notes(request)
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Revision notes error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate revision notes")


@router.post("/practice-questions", response_model=StudyContentResponse)
async def generate_practice_questions(
    request: PracticeQuestionsRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate practice questions from selected documents."""
    start_time = time.time()

    try:
        from app.services.study_service import StudyService

        study_service = StudyService(db)
        result = await study_service.practice_questions(request)
        result.processing_time_ms = int((time.time() - start_time) * 1000)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Practice questions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate practice questions")
