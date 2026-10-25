"""
Chat-related Pydantic schemas.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Chat request schema."""
    question: str = Field(..., min_length=1, max_length=10000, description="Student question")
    document_ids: list[str] = Field(default=[], description="Document IDs to search")
    conversation_id: Optional[str] = Field(default=None, description="Existing conversation ID")
    user_id: Optional[str] = Field(default=None, description="User email or identifier")
    mode: str = Field(
        default="documents_only",
        description="Answer mode: 'documents_only' or 'documents_web'",
    )
    enable_fact_check: bool = Field(
        default=False, description="Enable external fact checking"
    )


class CitationResponse(BaseModel):
    """Citation in a chat response."""
    source_type: str  # "document" or "web"
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    filename: Optional[str] = None
    page_number: Optional[int] = None
    snippet: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    relevance_score: Optional[float] = None


class ClaimVerification(BaseModel):
    """Verification result for a single claim."""
    claim: str
    verdict: str  # SUPPORTED, CONTRADICTED, NOT_ENOUGH_EVIDENCE
    source_ids: list[str] = []
    explanation: Optional[str] = None


class ContextVerificationResult(BaseModel):
    """Context verification output."""
    status: str  # SUFFICIENT, PARTIALLY_SUFFICIENT, INSUFFICIENT, CONFLICTING
    relevance: str  # HIGH, MEDIUM, LOW, NONE
    missing_information: list[str] = []
    conflicts_detected: bool = False
    conflict_details: Optional[str] = None
    supporting_chunk_ids: list[str] = []
    reason: str = ""


class AnswerVerificationResult(BaseModel):
    """Answer verification output."""
    status: str  # VERIFIED, NEEDS_REVISION, UNVERIFIABLE
    claims: list[ClaimVerification] = []
    unsupported_claims: list[str] = []
    overall_confidence: Optional[float] = None


class ChatResponse(BaseModel):
    """Chat response schema."""
    answer: str
    conversation_id: str
    message_id: str
    provenance: str  # "documents", "documents_web", "web", "general_ai", "insufficient"
    citations: list[CitationResponse] = []
    context_verification: Optional[ContextVerificationResult] = None
    answer_verification: Optional[AnswerVerificationResult] = None
    web_fallback_used: bool = False
    intent: Optional[str] = None
    response_format: Optional[str] = None
    structured_content: Optional[Any] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Message response."""
    id: str
    role: str
    content: str
    timestamp: datetime
    provenance: Optional[str] = None
    verification_status: Optional[str] = None
    intent: Optional[str] = None
    response_format: Optional[str] = None
    structured_content: Optional[Any] = None
    citations: list[CitationResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    """Detailed conversation with messages."""
    conversation: ConversationResponse
    messages: list[MessageResponse] = []


class ConversationListResponse(BaseModel):
    """List of conversations."""
    conversations: list[ConversationResponse]
    total: int


class FeedbackRequest(BaseModel):
    """User feedback on an answer."""
    message_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    comment: Optional[str] = Field(default=None, max_length=2000)
