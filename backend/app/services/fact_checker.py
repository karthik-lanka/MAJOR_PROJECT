"""
Fact checking service for verifying claims against external trusted sources.
"""

import asyncio
import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FactCheckerService:
    """Verify factual claims against external trusted sources."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_generation_model

    async def check_claim(
        self,
        claim: str,
        source_context: str,
        external_evidence: Optional[str] = None,
    ) -> dict:
        """
        Check a factual claim against external knowledge.

        Returns:
            dict with status (CORROBORATED, CONTRADICTED, INCONCLUSIVE),
            explanation, and source info.
        """
        prompt = f"""You are a fact-checking system. Analyze the following claim from a student's
uploaded document and determine if it is factually accurate.

CLAIM FROM DOCUMENT: {claim}

DOCUMENT CONTEXT:
{source_context[:2000]}

{f"EXTERNAL EVIDENCE:{chr(10)}{external_evidence[:2000]}" if external_evidence else ""}

Respond with a JSON object (no markdown, raw JSON only):
{{
    "status": "CORROBORATED" | "CONTRADICTED" | "INCONCLUSIVE",
    "document_states": "what the document claims",
    "factual_finding": "what is actually correct based on established knowledge",
    "explanation": "brief explanation of any discrepancy",
    "confidence": "HIGH" | "MEDIUM" | "LOW",
    "recommendation": "what the student should know about this claim"
}}

Guidelines:
- CORROBORATED: The claim aligns with established factual knowledge.
- CONTRADICTED: The claim conflicts with well-established facts.
- INCONCLUSIVE: Cannot determine if the claim is accurate or not.
- Be honest about uncertainty. Not everything can be fact-checked.
- Distinguish between factual errors and matters of interpretation.
- For technical claims, reference established standards or definitions."""

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0]

            return json.loads(text.strip())

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Fact checking failed: {e}")
            return {
                "status": "INCONCLUSIVE",
                "explanation": f"Fact check could not be completed: {str(e)[:200]}",
                "confidence": "LOW",
            }

    async def check_claims_batch(
        self,
        claims: list[dict],
    ) -> list[dict]:
        """Check multiple claims."""
        results = []
        for claim_data in claims:
            result = await self.check_claim(
                claim=claim_data.get("claim", ""),
                source_context=claim_data.get("context", ""),
                external_evidence=claim_data.get("external_evidence"),
            )
            result["original_claim"] = claim_data.get("claim", "")
            results.append(result)
        return results
