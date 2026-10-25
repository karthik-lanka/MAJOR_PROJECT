"""
Study-related Pydantic schemas for summaries, explanations, revision notes, etc.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class SummarizeRequest(BaseModel):
    """Request to summarize a document or section."""
    document_ids: list[str] = Field(..., min_length=1, description="Documents to summarize")
    detail_level: str = Field(
        default="standard",
        description="Summary detail: 'brief', 'standard', or 'detailed'",
    )
    section: Optional[str] = Field(default=None, description="Specific section to summarize")
    topic: Optional[str] = Field(default=None, description="Specific concept or topic to summarize")
    max_length: Optional[int] = Field(default=None, description="Maximum summary length in words")


class ExplainRequest(BaseModel):
    """Request to explain a concept."""
    concept: str = Field(..., min_length=1, description="Concept to explain")
    document_ids: list[str] = Field(default=[], description="Reference documents")
    level: str = Field(
        default="standard",
        description="Explanation level: 'simple', 'standard', 'advanced'",
    )
    include_examples: bool = Field(default=True, description="Include examples")


class RevisionNotesRequest(BaseModel):
    """Request to generate revision notes."""
    document_ids: list[str] = Field(..., min_length=1, description="Documents to create notes from")
    topics: list[str] = Field(default=[], description="Specific topics to focus on")
    format: str = Field(
        default="bullet_points",
        description="Format: 'bullet_points', 'detailed', 'exam_ready', 'flashcards'",
    )


class PracticeQuestionsRequest(BaseModel):
    """Request to generate practice questions."""
    document_ids: list[str] = Field(..., min_length=1, description="Source documents")
    question_type: str = Field(
        default="mixed",
        description="Type: 'mcq', 'short_answer', 'long_answer', 'true_false', 'fill_blanks', 'mixed'",
    )
    count: int = Field(default=10, ge=1, le=50, description="Number of questions")
    difficulty: str = Field(
        default="medium",
        description="Difficulty: 'easy', 'medium', 'hard', 'mixed'",
    )
    topics: list[str] = Field(default=[], description="Specific topics")


class MCQOption(BaseModel):
    """A single MCQ option."""
    id: str
    text: str


class MCQQuestion(BaseModel):
    """A multiple-choice question."""
    id: str
    question: str
    options: list[MCQOption]
    correct_option: str
    explanation: str
    citations: list[str] = []
    difficulty: Optional[str] = None
    topic: Optional[str] = None


class Flashcard(BaseModel):
    """A flashcard item."""
    id: str
    front: str  # Question or term
    back: str  # Answer or definition
    hint: Optional[str] = None
    source_reference: Optional[str] = None
    topic: Optional[str] = None


class StudyContentResponse(BaseModel):
    """General study content response."""
    content_type: str  # "summary", "explanation", "revision_notes", etc.
    title: str
    content: str  # Main text content
    structured_content: Optional[Any] = None  # Structured data (MCQs, tables, flashcards)
    citations: list[dict] = []
    document_ids: list[str] = []
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
