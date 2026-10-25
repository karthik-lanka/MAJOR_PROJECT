"""
Chat and conversation API routes.
Handles question answering, conversation management, and feedback.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.database_models import (
    Conversation,
    Message,
    Citation,
    Feedback,
    MessageRole,
    SourceType,
)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ConversationResponse,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageResponse,
    FeedbackRequest,
)
from app.schemas.common import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])


@router.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint. Processes a student question through the full RAG pipeline:
    1. Detect intent
    2. Retrieve relevant context
    3. Verify context sufficiency
    4. Generate answer
    5. Verify answer claims
    6. Apply fallback if needed
    7. Return with citations
    """
    start_time = time.time()

    try:
        from app.services.chat_orchestrator import ChatOrchestratorService

        orchestrator = ChatOrchestratorService(db)
        response = await orchestrator.process_question(request)
        response.processing_time_ms = int((time.time() - start_time) * 1000)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again.",
        )


@router.get("/api/conversations", response_model=ConversationListResponse)
async def list_conversations(
    user_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List conversations strictly for the authenticated user. Never expose other users' history."""
    if not user_id:
        return ConversationListResponse(conversations=[], total=0)

    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    conversations = result.scalars().all()

    conv_responses = []
    for conv in conversations:
        msg_count = (await db.execute(
            select(func.count()).select_from(Message).where(
                Message.conversation_id == conv.id
            )
        )).scalar() or 0

        conv_resp = ConversationResponse(
            id=conv.id,
            title=conv.title,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=msg_count,
        )
        conv_responses.append(conv_resp)

    return ConversationListResponse(
        conversations=conv_responses,
        total=len(conv_responses),
    )


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a conversation with all its messages."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages).selectinload(Message.citations))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = sorted(conversation.messages, key=lambda m: m.timestamp)

    msg_responses = []
    for msg in messages:
        citations = [
            CitationResponse(
                source_type=c.source_type.value,
                document_id=c.document_id,
                chunk_id=c.chunk_id,
                filename=c.filename,
                page_number=c.page_number,
                snippet=c.snippet,
                url=c.url,
                title=c.title,
                relevance_score=c.relevance_score,
            )
            for c in msg.citations
        ]

        import json
        structured = None
        if msg.structured_content:
            try:
                structured = json.loads(msg.structured_content)
            except (json.JSONDecodeError, TypeError):
                structured = None

        msg_responses.append(MessageResponse(
            id=msg.id,
            role=msg.role.value,
            content=msg.content,
            timestamp=msg.timestamp,
            provenance=msg.provenance,
            verification_status=msg.verification_status.value if msg.verification_status else None,
            intent=msg.intent,
            response_format=msg.response_format,
            structured_content=structured,
            citations=citations,
        ))

    msg_count = len(msg_responses)

    conv_resp = ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=msg_count,
    )

    return ConversationDetailResponse(
        conversation=conv_resp,
        messages=msg_responses,
    )


@router.delete("/api/conversations/{conversation_id}", response_model=APIResponse)
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()

    return APIResponse(
        success=True,
        message="Conversation deleted successfully",
    )


@router.post("/api/feedback", response_model=APIResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on an answer."""
    # Verify message exists
    result = await db.execute(
        select(Message).where(Message.id == request.message_id)
    )
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    feedback = Feedback(
        message_id=request.message_id,
        rating=request.rating,
        comment=request.comment,
    )
    db.add(feedback)
    await db.commit()

    return APIResponse(
        success=True,
        message="Feedback submitted. Thank you!",
    )
