"""
Context verification service.
Assesses relevance, sufficiency, and detects conflicts in retrieved evidence.
"""

import asyncio
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.llm_utils import generate_content_with_retry
from app.schemas.chat import ContextVerificationResult
from app.services.retrieval_service import RetrievedChunk

logger = logging.getLogger(__name__)


class ContextVerifierService:
    """Verify the quality and sufficiency of retrieved context."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_generation_model

    async def verify_context(
        self,
        question: str,
        chunks: list[RetrievedChunk],
    ) -> ContextVerificationResult:
        """
        Assess whether retrieved chunks provide sufficient, relevant evidence.

        Checks:
        1. Relevance - are chunks actually useful for answering?
        2. Sufficiency - is there enough information?
        3. Conflicts - do chunks contradict each other?
        4. Missing info - what important aspects are not covered?
        """
        if not chunks:
            return ContextVerificationResult(
                status="INSUFFICIENT",
                relevance="NONE",
                missing_information=["No relevant passages were found in the uploaded documents."],
                conflicts_detected=False,
                supporting_chunk_ids=[],
                reason="No chunks retrieved from the document index.",
            )

        # Build context for the verifier
        context_text = self._build_context_text(chunks)

        prompt = f"""You are an evidence verification system. Analyze the retrieved passages and determine
if they provide sufficient, relevant evidence to answer the student's question.

QUESTION: {question}

RETRIEVED PASSAGES:
{context_text}

Analyze the passages and respond with a JSON object (no markdown formatting, just raw JSON):
{{
    "status": "SUFFICIENT" | "PARTIALLY_SUFFICIENT" | "INSUFFICIENT" | "CONFLICTING",
    "relevance": "HIGH" | "MEDIUM" | "LOW" | "NONE",
    "missing_information": ["list of important aspects not covered by the passages"],
    "conflicts_detected": true/false,
    "conflict_details": "description of any conflicts between passages, or null",
    "supporting_chunk_ids": ["IDs of chunks that directly support answering the question"],
    "reason": "concise explanation of your assessment"
}}

Guidelines:
- status=SUFFICIENT: Passages contain enough information to fully answer the question.
- status=PARTIALLY_SUFFICIENT: Some relevant information exists but the answer would be incomplete.
- status=INSUFFICIENT: Passages do not contain relevant information for this question.
- status=CONFLICTING: Passages contain contradictory information about the same topic.
- Be conservative: if in doubt between SUFFICIENT and PARTIALLY_SUFFICIENT, choose PARTIALLY_SUFFICIENT.
- Only list chunks as supporting if they directly relate to the question.
- Do not fabricate missing information; only note genuinely missing aspects."""

        try:
            response = await generate_content_with_retry(
                self.client,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )

            return self._parse_verification_response(response.text, chunks)

        except Exception as e:
            logger.error(f"Context verification failed: {e}")
            # Default to partially sufficient on error so we still try to answer
            return ContextVerificationResult(
                status="PARTIALLY_SUFFICIENT",
                relevance="MEDIUM",
                missing_information=[],
                conflicts_detected=False,
                supporting_chunk_ids=[c.chunk_id for c in chunks],
                reason=f"Verification could not be completed: {str(e)[:200]}",
            )

    def _build_context_text(self, chunks: list[RetrievedChunk]) -> str:
        """Format retrieved chunks for the verification prompt."""
        parts = []
        for chunk in chunks:
            header = f"[Chunk ID: {chunk.chunk_id}]"
            if chunk.filename:
                header += f" [File: {chunk.filename}]"
            if chunk.page_number:
                header += f" [Page: {chunk.page_number}]"
            header += f" [Score: {chunk.score:.3f}]"

            parts.append(f"{header}\n{chunk.text}\n")

        return "\n---\n".join(parts)

    def _parse_verification_response(
        self,
        response_text: str,
        chunks: list[RetrievedChunk],
    ) -> ContextVerificationResult:
        """Parse the LLM's verification response."""
        try:
            # Clean the response text
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0] if "```" in text else text
            text = text.strip()

            data = json.loads(text)

            # Validate chunk IDs
            valid_ids = {c.chunk_id for c in chunks}
            supporting_ids = [
                cid for cid in data.get("supporting_chunk_ids", [])
                if cid in valid_ids
            ]

            return ContextVerificationResult(
                status=data.get("status", "PARTIALLY_SUFFICIENT"),
                relevance=data.get("relevance", "MEDIUM"),
                missing_information=data.get("missing_information", []),
                conflicts_detected=data.get("conflicts_detected", False),
                conflict_details=data.get("conflict_details"),
                supporting_chunk_ids=supporting_ids,
                reason=data.get("reason", ""),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse verification response: {e}")
            return ContextVerificationResult(
                status="PARTIALLY_SUFFICIENT",
                relevance="MEDIUM",
                missing_information=[],
                conflicts_detected=False,
                supporting_chunk_ids=[c.chunk_id for c in chunks],
                reason="Verification response could not be parsed; using all retrieved passages.",
            )
