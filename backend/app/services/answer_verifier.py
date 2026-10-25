"""
Answer verification service.
Extracts claims from generated answers and verifies them against evidence.
"""

import asyncio
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.core.llm_utils import generate_content_with_retry
from app.schemas.chat import AnswerVerificationResult, ClaimVerification
from app.services.retrieval_service import RetrievedChunk

logger = logging.getLogger(__name__)


class AnswerVerifierService:
    """Verify generated answers against source evidence."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_generation_model
        self.max_retries = 2

    async def verify_answer(
        self,
        question: str,
        answer: str,
        chunks: list[RetrievedChunk],
        citations_used: list[str],
    ) -> AnswerVerificationResult:
        """
        Verify that a generated answer is supported by the retrieved evidence.

        Steps:
        1. Extract factual claims from the answer.
        2. Match each claim to supporting evidence.
        3. Classify each claim as SUPPORTED, CONTRADICTED, or NOT_ENOUGH_EVIDENCE.
        4. Check that cited sources actually support the claims.
        """
        if not chunks:
            return AnswerVerificationResult(
                status="UNVERIFIABLE",
                claims=[],
                unsupported_claims=[],
                overall_confidence=0.0,
            )

        context_text = self._build_evidence_text(chunks)

        prompt = f"""You are an answer verification system. Your job is to check whether
a generated answer is faithfully supported by the source evidence.

QUESTION: {question}

GENERATED ANSWER:
{answer}

SOURCE EVIDENCE:
{context_text}

CITED SOURCES: {json.dumps(citations_used)}

Analyze the answer and respond with a JSON object (no markdown, just raw JSON):
{{
    "status": "VERIFIED" | "NEEDS_REVISION" | "UNVERIFIABLE",
    "claims": [
        {{
            "claim": "the specific factual claim from the answer",
            "verdict": "SUPPORTED" | "CONTRADICTED" | "NOT_ENOUGH_EVIDENCE",
            "source_ids": ["chunk_ids that support or contradict this claim"],
            "explanation": "brief explanation of the verdict"
        }}
    ],
    "unsupported_claims": ["list of claims not supported by evidence"],
    "overall_confidence": 0.0-1.0
}}

Guidelines:
- Extract the key factual claims from the answer (not opinions or explanations).
- For each claim, check if the source evidence supports it.
- SUPPORTED: evidence directly states or strongly implies this claim.
- CONTRADICTED: evidence states the opposite or is incompatible.
- NOT_ENOUGH_EVIDENCE: evidence does not address this claim.
- Verify that cited sources actually contain the referenced information.
- overall_confidence should reflect the proportion of supported claims.
- status=VERIFIED if most claims are supported and none are contradicted.
- status=NEEDS_REVISION if any claim is contradicted or many lack evidence.
- status=UNVERIFIABLE if evidence is too sparse to judge."""

        try:
            response = await generate_content_with_retry(
                self.client,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=2048,
                ),
            )

            return self._parse_verification(response.text, chunks)

        except Exception as e:
            logger.error(f"Answer verification failed: {e}")
            return AnswerVerificationResult(
                status="UNVERIFIABLE",
                claims=[],
                unsupported_claims=[],
                overall_confidence=None,
            )

    async def verify_and_correct(
        self,
        question: str,
        answer: str,
        chunks: list[RetrievedChunk],
        citations_used: list[str],
    ) -> tuple[AnswerVerificationResult, Optional[str]]:
        """
        Verify and attempt correction if verification fails.

        Returns:
            Tuple of (verification_result, corrected_answer_or_None)
        """
        verification = await self.verify_answer(question, answer, chunks, citations_used)

        if verification.status == "VERIFIED":
            return verification, None

        if verification.status == "NEEDS_REVISION" and verification.unsupported_claims:
            # Try to correct the answer
            for attempt in range(self.max_retries):
                corrected = await self._correct_answer(
                    question, answer, verification, chunks
                )
                if corrected:
                    # Re-verify the corrected answer
                    re_verification = await self.verify_answer(
                        question, corrected, chunks, citations_used
                    )
                    if re_verification.status == "VERIFIED":
                        return re_verification, corrected

                    # Use the corrected version if it's better
                    if (
                        re_verification.overall_confidence
                        and verification.overall_confidence
                        and re_verification.overall_confidence > verification.overall_confidence
                    ):
                        return re_verification, corrected

            logger.info("Answer correction did not achieve verification after retries")

        return verification, None

    async def _correct_answer(
        self,
        question: str,
        answer: str,
        verification: AnswerVerificationResult,
        chunks: list[RetrievedChunk],
    ) -> Optional[str]:
        """Attempt to correct an answer by removing or fixing unsupported claims."""
        context_text = self._build_evidence_text(chunks)

        unsupported = verification.unsupported_claims
        contradicted = [
            c.claim for c in verification.claims if c.verdict == "CONTRADICTED"
        ]

        prompt = f"""You are correcting an AI-generated answer that contains unsupported or incorrect claims.

ORIGINAL QUESTION: {question}

ORIGINAL ANSWER:
{answer}

PROBLEMS FOUND:
- Unsupported claims: {json.dumps(unsupported)}
- Contradicted claims: {json.dumps(contradicted)}

SOURCE EVIDENCE:
{context_text}

Rewrite the answer to:
1. Remove or correct the unsupported/contradicted claims.
2. Only state what is supported by the evidence.
3. Clearly note where information is insufficient.
4. Maintain the helpful, student-friendly tone.
5. Preserve correct citations.

Respond with ONLY the corrected answer text."""

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
            return response.text.strip()
        except Exception as e:
            logger.error(f"Answer correction failed: {e}")
            return None

    def _build_evidence_text(self, chunks: list[RetrievedChunk]) -> str:
        """Format chunks for verification prompt."""
        parts = []
        for chunk in chunks:
            header = f"[ID: {chunk.chunk_id}]"
            if chunk.filename:
                header += f" [File: {chunk.filename}]"
            if chunk.page_number:
                header += f" [Page: {chunk.page_number}]"
            parts.append(f"{header}\n{chunk.text}")
        return "\n\n---\n\n".join(parts)

    def _parse_verification(
        self,
        response_text: str,
        chunks: list[RetrievedChunk],
    ) -> AnswerVerificationResult:
        """Parse the verification response."""
        try:
            text = response_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            data = json.loads(text)

            valid_ids = {c.chunk_id for c in chunks}

            claims = []
            for claim_data in data.get("claims", []):
                source_ids = [
                    sid for sid in claim_data.get("source_ids", [])
                    if sid in valid_ids
                ]
                claims.append(ClaimVerification(
                    claim=claim_data.get("claim", ""),
                    verdict=claim_data.get("verdict", "NOT_ENOUGH_EVIDENCE"),
                    source_ids=source_ids,
                    explanation=claim_data.get("explanation"),
                ))

            return AnswerVerificationResult(
                status=data.get("status", "UNVERIFIABLE"),
                claims=claims,
                unsupported_claims=data.get("unsupported_claims", []),
                overall_confidence=data.get("overall_confidence"),
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse verification response: {e}")
            return AnswerVerificationResult(
                status="UNVERIFIABLE",
                claims=[],
                unsupported_claims=[],
                overall_confidence=None,
            )
