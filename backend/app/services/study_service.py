"""
Study assistance service.
Handles summarization, concept explanations, revision notes, and practice question generation.
"""

import asyncio
import json
import logging
import re
from typing import Optional

from google import genai
from google.genai import types
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.llm_utils import generate_content_with_retry
from app.models.database_models import Chunk, Document
from app.schemas.study import (
    SummarizeRequest,
    ExplainRequest,
    RevisionNotesRequest,
    PracticeQuestionsRequest,
    StudyContentResponse,
)
from app.services.retrieval_service import RetrievalService, RetrievedChunk

logger = logging.getLogger(__name__)


class StudyService:
    """Service providing academic study aids grounded in uploaded materials."""

    def __init__(self, db: AsyncSession):
        self.db = db
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_generation_model
        self.retrieval_service = RetrievalService()

    async def summarize(self, request: SummarizeRequest) -> StudyContentResponse:
        """Generate a concise or detailed summary of documents/sections."""
        topic_filter = request.topic or request.section
        if topic_filter:
            chunks = await self.retrieval_service.retrieve_for_context(
                query=topic_filter,
                document_ids=request.document_ids,
            )
            if not chunks:
                chunks = await self._get_document_chunks(request.document_ids, max_chunks=25)
        else:
            chunks = await self._get_document_chunks(request.document_ids, max_chunks=25)

        if not chunks:
            return StudyContentResponse(
                content_type="summary",
                title="Summary",
                content="No content found in the selected documents to summarize.",
                document_ids=request.document_ids,
                error="No text available for the specified document(s).",
            )

        context_text = self._build_context(chunks)
        length_guidance = ""
        if request.max_length:
            length_guidance = f"Keep the summary under {request.max_length} words."

        prompt = f"""You are an expert academic tutor. Summarize the following study material.

DETAIL LEVEL: {request.detail_level} (options: brief, standard, detailed)
{f"SPECIFIC TOPIC / FOCUS: {topic_filter}" if topic_filter else ""}
{length_guidance}

GUIDELINES:
- Base the summary STRICTLY on the source text provided.
- Highlight key definitions, main theorems/arguments, and core takeaways.
- Structure with clear markdown headings and bullet points.
- Cite sources as [Source: filename, Page X].

SOURCE MATERIAL:
{context_text}

Generate a clear, high-quality academic summary:"""

        try:
            response = await generate_content_with_retry(
                self.client,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )
            summary_text = response.text.strip()
            citations = self._build_citations_list(chunks)

            return StudyContentResponse(
                content_type="summary",
                title=f"Summary ({request.detail_level.capitalize()})",
                content=summary_text,
                citations=citations,
                document_ids=request.document_ids,
            )
        except Exception as e:
            logger.error(f"Summarize error: {e}", exc_info=True)
            return StudyContentResponse(
                content_type="summary",
                title="Summary Error",
                content="Failed to generate summary due to an internal error.",
                document_ids=request.document_ids,
                error=str(e),
            )

    async def explain(self, request: ExplainRequest) -> StudyContentResponse:
        """Explain a concept using uploaded document context."""
        chunks: list[RetrievedChunk] = []
        if request.document_ids:
            chunks = await self.retrieval_service.retrieve_for_context(
                query=request.concept,
                document_ids=request.document_ids,
            )
        else:
            chunks = await self.retrieval_service.retrieve_for_context(
                query=request.concept,
            )

        context_text = self._build_context(chunks) if chunks else "(No direct document matches found; providing general academic explanation)"

        prompt = f"""You are an enthusiastic and clear academic educator. Explain the following concept:

CONCEPT: {request.concept}
EXPLANATION LEVEL: {request.level} (options: simple, standard, advanced)
INCLUDE EXAMPLES: {request.include_examples}

SOURCE MATERIAL FROM STUDENT'S DOCUMENTS:
{context_text}

GUIDELINES:
- If document evidence exists, ground the explanation in the provided materials.
- Cite passages using [Source: filename, Page X].
- Break down complex terms with intuition, real-world analogies, and step-by-step logic.
- Use clean Markdown formatting with clear subheadings."""

        try:
            response = await generate_content_with_retry(
                self.client,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
            citations = self._build_citations_list(chunks)

            return StudyContentResponse(
                content_type="explanation",
                title=f"Explanation: {request.concept}",
                content=response.text.strip(),
                citations=citations,
                document_ids=request.document_ids,
            )
        except Exception as e:
            logger.error(f"Explain error: {e}", exc_info=True)
            return StudyContentResponse(
                content_type="explanation",
                title=f"Explanation: {request.concept}",
                content="Failed to generate explanation.",
                document_ids=request.document_ids,
                error=str(e),
            )

    async def revision_notes(self, request: RevisionNotesRequest) -> StudyContentResponse:
        """Generate high-yield revision notes."""
        chunks = await self._get_document_chunks(request.document_ids, max_chunks=30)
        context_text = self._build_context(chunks)

        prompt = f"""You are a master study coach. Generate comprehensive, exam-ready revision notes.

FORMAT: {request.format} (e.g. bullet_points, detailed, exam_ready, flashcards)
FOCUS TOPICS: {', '.join(request.topics) if request.topics else 'All major topics in the documents'}

SOURCE MATERIAL:
{context_text}

INSTRUCTIONS:
1. Extract all key formulas, definitions, mnemonics, and high-yield concepts.
2. Highlight common exam pitfalls and "must-know" points.
3. Organize logically with clear headings, bullet points, and code/math blocks if applicable.
4. Format with beautiful, easy-to-read Markdown."""

        try:
            response = await generate_content_with_retry(
                self.client,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=4096,
                ),
            )
            citations = self._build_citations_list(chunks)

            return StudyContentResponse(
                content_type="revision_notes",
                title="High-Yield Revision Notes",
                content=response.text.strip(),
                citations=citations,
                document_ids=request.document_ids,
            )
        except Exception as e:
            logger.error(f"Revision notes error: {e}", exc_info=True)
            return StudyContentResponse(
                content_type="revision_notes",
                title="Revision Notes",
                content="Failed to generate revision notes.",
                document_ids=request.document_ids,
                error=str(e),
            )

    async def practice_questions(
        self, request: PracticeQuestionsRequest
    ) -> StudyContentResponse:
        """Generate practice questions (MCQs, short answer, mixed) with answers & explanations."""
        if request.topics:
            topic_query = " ".join(request.topics)
            chunks = await self.retrieval_service.retrieve_for_context(
                query=topic_query,
                document_ids=request.document_ids,
            )
            if not chunks:
                chunks = await self._get_document_chunks(request.document_ids, max_chunks=25)
        else:
            chunks = await self._get_document_chunks(request.document_ids, max_chunks=25)

        context_text = self._build_context(chunks)

        prompt = f"""You are an exam setter and academic examiner. Generate {request.count} practice questions grounded directly in the source material.

QUESTION TYPE: {request.question_type} (options: mcq, short_answer, mixed)
DIFFICULTY: {request.difficulty}
TOPICS: {', '.join(request.topics) if request.topics else 'Cover broad range from the document'}

SOURCE MATERIAL:
{context_text}

CRITICAL FORMATTING RULES:
1. Format ALL Multiple-Choice Questions (MCQs) strictly inside the JSON_DATA array below.
2. DO NOT spoil or write the MCQ questions and answers in plain text! Users interact with them through clickable quiz cards.
3. If mixed question type is selected, put conceptual short-answer questions in the text, and all MCQs in JSON_DATA.

JSON_DATA:
[
  {{
    "id": "1",
    "question": "Question text?",
    "options": [
      {{"id": "A", "text": "Option A"}},
      {{"id": "B", "text": "Option B"}},
      {{"id": "C", "text": "Option C"}},
      {{"id": "D", "text": "Option D"}}
    ],
    "correct_option": "A",
    "explanation": "Detailed explanation here",
    "difficulty": "{request.difficulty}"
  }}
]"""

        try:
            response = await generate_content_with_retry(
                self.client,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=6000,
                ),
            )

            full_text = response.text.strip()
            structured_data = None
            content_text = full_text

            if "JSON_DATA:" in full_text:
                parts = full_text.split("JSON_DATA:", 1)
                content_text = parts[0].strip()
                json_part = parts[1].strip()
                if json_part.startswith("```"):
                    json_part = json_part.split("\n", 1)[1] if "\n" in json_part else json_part
                    json_part = json_part.rsplit("```", 1)[0]
                try:
                    structured_data = json.loads(json_part.strip())
                except Exception as ex:
                    logger.warning(f"Could not parse quiz JSON: {ex}")
            else:
                raw_json = full_text.strip()
                if raw_json.startswith("```"):
                    raw_json = raw_json.split("\n", 1)[1] if "\n" in raw_json else raw_json
                    raw_json = raw_json.rsplit("```", 1)[0]
                raw_json = raw_json.strip()
                if raw_json.startswith("[") and raw_json.endswith("]"):
                    try:
                        structured_data = json.loads(raw_json)
                        content_text = ""
                    except Exception as ex:
                        logger.warning(f"Could not parse direct JSON: {ex}")

            # Fallback: if structured_data was not extracted, parse any markdown MCQs directly
            if not structured_data:
                mcqs, clean_text = self._parse_mcqs_from_text(content_text)
                if mcqs:
                    structured_data = mcqs
                    content_text = clean_text

            # If it's an MCQ-only request and structured questions exist, keep content_text clean
            if structured_data and request.question_type == 'mcq':
                content_text = ""

            citations = self._build_citations_list(chunks)

            return StudyContentResponse(
                content_type="practice_questions",
                title=f"Practice Questions ({request.question_type.upper()})",
                content=content_text,
                structured_content=structured_data,
                citations=citations,
                document_ids=request.document_ids,
            )
        except Exception as e:
            logger.error(f"Practice questions error: {e}", exc_info=True)
            return StudyContentResponse(
                content_type="practice_questions",
                title="Practice Questions",
                content="Failed to generate practice questions.",
                document_ids=request.document_ids,
                error=str(e),
            )

    def _parse_mcqs_from_text(self, text: str) -> tuple[list[dict], str]:
        """Extract MCQs formatted in markdown and return structured list and remaining text."""
        if not text:
            return [], ""
        mcq_pattern = re.compile(
            r'(?:###?\s*)?(?:Question\s*\d*[:.]?\s*(?:\(MCQ\)|Multiple Choice[^\n]*)?\n+)?'
            r'([^\n]+(?:\n(?![•\-\*]?\s*[A-D][\)\.])[^\n]+)*)\n+'
            r'[•\-\*]?\s*A[\)\.]\s*([^\n]+)\n+'
            r'[•\-\*]?\s*B[\)\.]\s*([^\n]+)\n+'
            r'[•\-\*]?\s*C[\)\.]\s*([^\n]+)\n+'
            r'[•\-\*]?\s*D[\)\.]\s*([^\n]+)'
            r'(?:\n+[•\-\*]?\s*(?:Correct\s*(?:Option|Answer)|Answer)[:\s]*([A-D])\b[^\n]*)?'
            r'(?:\n+(?:Explanation|Reasoning)[:\s]*([^\n]+(?:\n(?!(?:Question|###|\d+\.))[^\n]+)*))?',
            re.IGNORECASE
        )
        mcqs = []
        blocks_to_remove = []
        for idx, match in enumerate(mcq_pattern.finditer(text)):
            q_text = match.group(1).strip()
            q_text = re.sub(r'^(?:Question\s*\d*[:.]?\s*(?:\(MCQ\)|Multiple Choice[^\n]*)?\s*)', '', q_text, flags=re.IGNORECASE).strip()
            optA = match.group(2).strip()
            optB = match.group(3).strip()
            optC = match.group(4).strip()
            optD = match.group(5).strip()
            correct = (match.group(6) or "A").strip().upper()
            explanation = (match.group(7) or "").strip()
            if q_text and optA and optB and optC and optD:
                mcqs.append({
                    "id": str(idx + 1),
                    "question": q_text,
                    "options": [
                        {"id": "A", "text": optA},
                        {"id": "B", "text": optB},
                        {"id": "C", "text": optC},
                        {"id": "D", "text": optD},
                    ],
                    "correct_option": correct,
                    "explanation": explanation,
                })
                blocks_to_remove.append(match.group(0))

        remaining = text
        for b in blocks_to_remove:
            remaining = remaining.replace(b, "")
        remaining = re.sub(r'#+\s*(?:Exam Questions and Solutions|Practice MCQs|Multiple Choice Questions)[^\n]*', '', remaining, flags=re.IGNORECASE).strip()
        return mcqs, remaining

    async def _get_document_chunks(
        self, document_ids: list[str], max_chunks: int = 25
    ) -> list[RetrievedChunk]:
        """Fetch chunks for specific documents directly from SQLite database."""
        result = await self.db.execute(
            select(Chunk, Document.filename)
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.document_id.in_(document_ids))
            .order_by(Chunk.document_id, Chunk.chunk_index)
            .limit(max_chunks)
        )
        rows = result.all()

        chunks = []
        for chunk, filename in rows:
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    text=chunk.chunk_text,
                    score=1.0,
                    page_number=chunk.page_number,
                    filename=filename,
                    section_heading=chunk.section_heading,
                    chunk_index=chunk.chunk_index,
                )
            )
        return chunks

    def _build_context(self, chunks: list[RetrievedChunk]) -> str:
        """Format chunks into readable text with source citations."""
        parts = []
        for c in chunks:
            hdr = f"[{c.filename or 'Document'}"
            if c.page_number:
                hdr += f", Page {c.page_number}"
            hdr += "]"
            parts.append(f"{hdr}\n{c.text}")
        return "\n\n---\n\n".join(parts)

    def _build_citations_list(self, chunks: list[RetrievedChunk]) -> list[dict]:
        """Convert chunks to citation dictionaries."""
        seen = set()
        citations = []
        for c in chunks:
            key = (c.document_id, c.page_number)
            if key not in seen:
                seen.add(key)
                citations.append({
                    "document_id": c.document_id,
                    "filename": c.filename,
                    "page_number": c.page_number,
                    "snippet": c.text[:200],
                })
        return citations
