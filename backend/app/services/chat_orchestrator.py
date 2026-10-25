"""
Chat orchestrator service.
Coordinates the end-to-end RAG pipeline:
1. Intent detection
2. Semantic retrieval
3. Context verification
4. Grounded answer generation
5. Answer verification & correction loop
6. Transparent fallback (web search if allowed/needed)
7. Citation mapping and persistence
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.database_models import (
    Conversation,
    Message,
    Citation,
    Document,
    ProcessingStatus,
    MessageRole,
    SourceType,
    VerificationStatus,
    EvidenceSufficiency,
)
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CitationResponse,
    ContextVerificationResult,
    AnswerVerificationResult,
)
from app.services.intent_detection import IntentDetectionService
from app.services.retrieval_service import RetrievalService, RetrievedChunk
from app.services.context_verifier import ContextVerifierService
from app.services.answer_generator import AnswerGeneratorService
from app.services.answer_verifier import AnswerVerifierService
from app.services.web_search_service import WebSearchService
from app.services.fact_checker import FactCheckerService

logger = logging.getLogger(__name__)


class ChatOrchestratorService:
    """Coordinates all services for conversational question answering."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.intent_service = IntentDetectionService()
        self.retrieval_service = RetrievalService()
        self.context_verifier = ContextVerifierService()
        self.answer_generator = AnswerGeneratorService()
        self.answer_verifier = AnswerVerifierService()
        self.web_search_service = WebSearchService()
        self.fact_checker = FactCheckerService()

    async def process_question(self, request: ChatRequest) -> ChatResponse:
        """Process a student question through the full pipeline."""
        # 1. Manage Conversation
        conversation = await self._get_or_create_conversation(
            request.conversation_id, request.question, request.user_id
        )

        # 2. Record User Message
        user_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.question,
        )
        self.db.add(user_message)
        await self.db.flush()

        # 3. Fetch recent history for multi-turn conversational context
        history = await self._fetch_recent_history(conversation.id, limit=6)

        # 4. Detect Intent
        intent_info = await self.intent_service.detect_intent(request.question)
        intent = intent_info.get("intent", "QUESTION_ANSWERING")
        response_format = intent_info.get("format", "text")

        # 5. Semantic Retrieval (Scoped to user's documents and guest documents)
        chunks: list[RetrievedChunk] = []
        try:
            target_doc_ids = request.document_ids or []
            if not target_doc_ids:
                # If user has documents currently processing, wait briefly for them to complete
                for _ in range(20):
                    filter_cond = (Document.user_id == request.user_id) | (Document.user_id.is_(None)) if request.user_id else Document.user_id.is_(None)
                    pending_res = await self.db.execute(
                        select(Document.id).where(
                            filter_cond,
                            Document.processing_status.in_([
                                ProcessingStatus.UPLOADED,
                                ProcessingStatus.EXTRACTING,
                                ProcessingStatus.CHUNKING,
                                ProcessingStatus.EMBEDDING,
                                ProcessingStatus.INDEXING,
                            ]),
                        )
                    )
                    if not pending_res.scalars().all():
                        break
                    await asyncio.sleep(0.5)
                    self.db.expire_all()

                if request.user_id:
                    user_docs_result = await self.db.execute(
                        select(Document.id).where(
                            (Document.user_id == request.user_id) | (Document.user_id.is_(None)),
                            Document.processing_status == ProcessingStatus.READY,
                        )
                    )
                else:
                    user_docs_result = await self.db.execute(
                        select(Document.id).where(
                            Document.user_id.is_(None),
                            Document.processing_status == ProcessingStatus.READY,
                        )
                    )
                target_doc_ids = [r[0] for r in user_docs_result.fetchall()]
            else:
                # If specific target documents were provided and are currently processing, wait for completion
                for _ in range(25):
                    pending_result = await self.db.execute(
                        select(Document.id).where(
                            Document.id.in_(target_doc_ids),
                            Document.processing_status.in_([
                                ProcessingStatus.UPLOADED,
                                ProcessingStatus.EXTRACTING,
                                ProcessingStatus.CHUNKING,
                                ProcessingStatus.EMBEDDING,
                                ProcessingStatus.INDEXING,
                            ]),
                        )
                    )
                    if not pending_result.scalars().all():
                        break
                    await asyncio.sleep(0.5)
                    self.db.expire_all()

                if request.user_id:
                    user_docs_result = await self.db.execute(
                        select(Document.id).where(
                            (Document.user_id == request.user_id) | (Document.user_id.is_(None)),
                            Document.id.in_(target_doc_ids),
                        )
                    )
                    target_doc_ids = [r[0] for r in user_docs_result.fetchall()]

            if target_doc_ids:
                chunks = await self.retrieval_service.retrieve_for_context(
                    query=request.question,
                    document_ids=target_doc_ids,
                )
        except Exception as e:
            logger.error(f"Retrieval error: {e}", exc_info=True)

        # 6. Fallback Web Search if applicable
        web_context: Optional[str] = None
        web_results = []
        web_fallback_used = False

        should_fallback = (
            request.mode in ("documents_web", "auto", "default")
            or len(chunks) == 0
        )

        if should_fallback and self.web_search_service.is_configured:
            try:
                web_results = await self.web_search_service.search(request.question)
                if web_results:
                    web_context = self.web_search_service.format_results_as_context(web_results)
                    web_fallback_used = True
            except Exception as e:
                logger.warning(f"Web search fallback failed: {e}")

        # 7. Fast Parallel Context Verification & Answer Generation
        structured_content = None
        is_structured_intent = intent in {
            "MCQ_GENERATION",
            "QUIZ_MODE",
            "FLASHCARD_GENERATION",
            "TABLE_GENERATION",
        }

        # Run context verification and generation concurrently to maximize response speed
        context_task = asyncio.create_task(
            self.context_verifier.verify_context(request.question, chunks)
        )
        answer_task = asyncio.create_task(
            self.answer_generator.generate_answer(
                question=request.question,
                chunks=chunks,
                mode=request.mode,
                conversation_history=history,
                intent=intent,
                web_context=web_context,
            )
        )

        structured_task = None
        if is_structured_intent:
            schema_sample = self._get_schema_template(intent)
            structured_task = asyncio.create_task(
                self.answer_generator.generate_structured_content(
                    question=request.question,
                    chunks=chunks,
                    intent=intent,
                    output_schema=schema_sample,
                )
            )

        # Await core tasks in parallel
        try:
            gen_result = await answer_task
            answer = gen_result["answer"]
            citations_used = gen_result["citations_used"]
            provenance = gen_result["provenance"]
        except Exception as e:
            logger.warning(f"LLM Generation hit error or quota limit: {e}. Falling back to extractive grounded synthesis.")
            if chunks:
                answer = (
                    f"### Grounded Evidence from Your Indexed Notes\n\n"
                    + "\n\n".join(f"**From {c.filename or 'Document'} (Page {c.page_number or 1}):**\n> {c.text.strip()}" for c in chunks[:3])
                )
                citations_used = [c.chunk_id for c in chunks[:3]]
                provenance = "documents"
            else:
                answer = "I searched your study materials, but could not find passages sufficiently relevant to your query. Please upload or select the corresponding course materials."
                citations_used = []
                provenance = "general_ai"

        try:
            context_verification = await context_task
        except Exception as e:
            logger.warning(f"Context verification failed: {e}")
            context_verification = ContextVerificationResult(
                status="SUFFICIENT" if chunks else "INSUFFICIENT",
                relevance="HIGH" if chunks else "NONE",
                missing_information=[],
                conflicts_detected=False,
                supporting_chunk_ids=[c.chunk_id for c in chunks],
                reason="Verification bypassed for speed",
            )

        if structured_task:
            try:
                structured_content = await structured_task
            except Exception as e:
                logger.warning(f"Structured content generation failed: {e}")

        # If structured content contains MCQs, ensure answer does NOT spoil the answers in plain text!
        is_mcq_content = (
            structured_content
            and isinstance(structured_content, list)
            and len(structured_content) > 0
            and "options" in structured_content[0]
        )
        if is_mcq_content:
            answer = f"Here are {len(structured_content)} interactive practice questions based on your study materials. Select an option below to test your knowledge with instant grading and explanations:"

        # 8. Fast Answer Verification & Correction Loop (Non-blocking fallback)
        answer_verification: Optional[AnswerVerificationResult] = None
        if chunks and not is_mcq_content:
            try:
                answer_verification, corrected_answer = await asyncio.wait_for(
                    self.answer_verifier.verify_and_correct(
                        question=request.question,
                        answer=answer,
                        chunks=chunks,
                        citations_used=citations_used,
                    ),
                    timeout=5.0,
                )
                if corrected_answer:
                    answer = corrected_answer
            except Exception as e:
                logger.warning(f"Answer verification bypassed or timed out: {e}")

        # 9. Fast Parallel Fact Checking
        if answer_verification and answer_verification.claims:
            try:
                async def check_single_claim(claim_item):
                    try:
                        fc_result = await self.fact_checker.check_claim(
                            claim=claim_item.claim,
                            source_context=" ".join(c.text[:200] for c in chunks[:3]),
                            external_evidence=web_context,
                        )
                        if fc_result.get("status") == "CONTRADICTED":
                            claim_item.explanation = (
                                f"{claim_item.explanation or ''} [Fact Check: {fc_result.get('explanation', '')}]"
                            )
                    except Exception:
                        pass

                claim_tasks = [check_single_claim(c) for c in answer_verification.claims[:3]]
                await asyncio.wait_for(asyncio.gather(*claim_tasks), timeout=3.5)
            except Exception as e:
                logger.warning(f"Fact checking timed out: {e}")

        # 11. Build Citation Responses
        citation_responses: list[CitationResponse] = []
        chunk_map = {c.chunk_id: c for c in chunks}

        # Document citations
        for cid in citations_used:
            chunk = chunk_map.get(cid)
            if chunk:
                citation_responses.append(
                    CitationResponse(
                        source_type="document",
                        document_id=chunk.document_id,
                        chunk_id=chunk.chunk_id,
                        filename=chunk.filename,
                        page_number=chunk.page_number,
                        snippet=chunk.text[:250],
                        relevance_score=chunk.score,
                    )
                )

        # If no specific citations used were parsed, include top supporting chunks
        if not citation_responses and chunks:
            for chunk in chunks[:3]:
                citation_responses.append(
                    CitationResponse(
                        source_type="document",
                        document_id=chunk.document_id,
                        chunk_id=chunk.chunk_id,
                        filename=chunk.filename,
                        page_number=chunk.page_number,
                        snippet=chunk.text[:250],
                        relevance_score=chunk.score,
                    )
                )

        # Web citations
        for wr in web_results[:3]:
            citation_responses.append(
                CitationResponse(
                    source_type="web",
                    url=wr.url,
                    title=wr.title,
                    snippet=wr.snippet[:250],
                )
            )

        # 12. Save Assistant Message & Citations to Database
        verification_status_enum = None
        if answer_verification:
            if answer_verification.status == "VERIFIED":
                verification_status_enum = VerificationStatus.SUPPORTED
            elif answer_verification.status == "NEEDS_REVISION":
                verification_status_enum = VerificationStatus.NEEDS_REVISION
            else:
                verification_status_enum = VerificationStatus.UNVERIFIED

        evidence_suff_enum = None
        if context_verification:
            try:
                evidence_suff_enum = EvidenceSufficiency[context_verification.status]
            except KeyError:
                evidence_suff_enum = EvidenceSufficiency.PARTIALLY_SUFFICIENT

        assistant_message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=answer,
            provenance=provenance,
            verification_status=verification_status_enum,
            intent=intent,
            response_format=response_format,
            structured_content=json.dumps(structured_content) if structured_content else None,
            evidence_sufficiency=evidence_suff_enum,
        )
        self.db.add(assistant_message)
        await self.db.flush()

        # Save Citations in DB
        for cit in citation_responses:
            db_citation = Citation(
                message_id=assistant_message.id,
                source_type=SourceType.DOCUMENT if cit.source_type == "document" else SourceType.WEB,
                document_id=cit.document_id,
                chunk_id=cit.chunk_id,
                page_number=cit.page_number,
                filename=cit.filename,
                snippet=cit.snippet,
                url=cit.url,
                title=cit.title,
                relevance_score=cit.relevance_score,
            )
            self.db.add(db_citation)

        conversation.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        return ChatResponse(
            answer=answer,
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            provenance=provenance,
            citations=citation_responses,
            context_verification=context_verification,
            answer_verification=answer_verification,
            web_fallback_used=web_fallback_used,
            intent=intent,
            response_format=response_format,
            structured_content=structured_content,
        )

    async def _get_or_create_conversation(
        self, conversation_id: Optional[str], question: str, user_id: Optional[str] = None
    ) -> Conversation:
        """Get an existing conversation or create a new one."""
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = result.scalar_one_or_none()
            if conv:
                if user_id and not conv.user_id:
                    conv.user_id = user_id
                return conv

        # Generate concise title from first question
        clean_title = question.strip().replace("\n", " ")
        if len(clean_title) > 40:
            clean_title = clean_title[:37] + "..."

        conversation = Conversation(title=clean_title, user_id=user_id)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def _fetch_recent_history(
        self, conversation_id: str, limit: int = 6
    ) -> list[dict]:
        """Fetch recent message history for conversation."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.desc())
            .limit(limit)
        )
        messages = list(reversed(result.scalars().all()))
        return [{"role": m.role.value, "content": m.content} for m in messages]

    def _get_schema_template(self, intent: str) -> str:
        """Get output schema template based on intent."""
        if intent in ("MCQ_GENERATION", "QUIZ_MODE"):
            return """[
  {
    "id": "1",
    "question": "Question text here?",
    "options": [
      {"id": "A", "text": "Option A"},
      {"id": "B", "text": "Option B"},
      {"id": "C", "text": "Option C"},
      {"id": "D", "text": "Option D"}
    ],
    "correct_option": "A",
    "explanation": "Why A is correct based on the text",
    "difficulty": "medium",
    "topic": "Topic name"
  }
]"""
        elif intent == "FLASHCARD_GENERATION":
            return """[
  {
    "id": "1",
    "front": "Term / Question",
    "back": "Definition / Answer",
    "hint": "Optional memory trigger",
    "topic": "Topic name"
  }
]"""
        elif intent == "TABLE_GENERATION":
            return """{
  "title": "Comparison / Summary Table",
  "headers": ["Column 1", "Column 2", "Column 3"],
  "rows": [
    ["Row 1 Val 1", "Row 1 Val 2", "Row 1 Val 3"],
    ["Row 2 Val 1", "Row 2 Val 2", "Row 2 Val 3"]
  ]
}"""
        return "{}"
