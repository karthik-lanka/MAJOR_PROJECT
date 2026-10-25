"""
SQLAlchemy database models for the Study Assistant.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Enum as SAEnum,
)
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums ---

class ProcessingStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    EXTRACTING = "EXTRACTING"
    CHUNKING = "CHUNKING"
    EMBEDDING = "EMBEDDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"
    DELETING = "DELETING"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SourceType(str, enum.Enum):
    DOCUMENT = "document"
    WEB = "web"
    GENERAL_AI = "general_ai"


class VerificationStatus(str, enum.Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_ENOUGH_EVIDENCE = "NOT_ENOUGH_EVIDENCE"
    NEEDS_REVISION = "NEEDS_REVISION"
    UNVERIFIED = "UNVERIFIED"


class EvidenceSufficiency(str, enum.Enum):
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"


# --- Models ---

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    user_id = Column(String, nullable=True, index=True)
    upload_timestamp = Column(DateTime, default=utc_now, nullable=False)
    processing_status = Column(
        SAEnum(ProcessingStatus),
        default=ProcessingStatus.UPLOADED,
        nullable=False,
    )
    page_count = Column(Integer, nullable=True)
    chunk_count = Column(Integer, default=0)
    content_hash = Column(String, nullable=True)
    storage_path = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    processing_completed_at = Column(DateTime, nullable=True)

    # Relationships
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    page_range_start = Column(Integer, nullable=True)
    page_range_end = Column(Integer, nullable=True)
    section_heading = Column(String, nullable=True)
    token_count = Column(Integer, nullable=True)
    content_hash = Column(String, nullable=True)
    embedding_model = Column(String, nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    pinecone_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String, default="New Conversation")
    user_id = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(SAEnum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=utc_now, nullable=False)
    provenance = Column(String, nullable=True)  # e.g., "documents", "web", "general_ai"
    verification_status = Column(SAEnum(VerificationStatus), nullable=True)
    intent = Column(String, nullable=True)  # Detected query intent
    response_format = Column(String, nullable=True)  # Response format type
    structured_content = Column(Text, nullable=True)  # JSON structured content for special formats
    evidence_sufficiency = Column(SAEnum(EvidenceSufficiency), nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    citations = relationship("Citation", back_populates="message", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(
        String, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    source_type = Column(SAEnum(SourceType), nullable=False)
    document_id = Column(String, nullable=True)
    chunk_id = Column(String, nullable=True)
    page_number = Column(Integer, nullable=True)
    filename = Column(String, nullable=True)
    snippet = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    message = relationship("Message", back_populates="citations")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(String, primary_key=True, default=generate_uuid)
    message_id = Column(String, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 or thumbs up/down
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
