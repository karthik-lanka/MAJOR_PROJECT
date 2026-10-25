"""
Intent detection service.
Classifies user queries to determine the appropriate response format.
"""

import asyncio
import json
import logging
import re
from typing import Optional

from google import genai
from google.genai import types

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Intent categories
INTENTS = {
    "QUESTION_ANSWERING",
    "MCQ_GENERATION",
    "QUIZ_MODE",
    "TABLE_GENERATION",
    "COMPARISON",
    "SUMMARIZATION",
    "REVISION_NOTES",
    "STEP_BY_STEP_EXPLANATION",
    "CONCEPT_EXPLANATION",
    "FLASHCARD_GENERATION",
    "PRACTICE_PROBLEMS",
    "TRUE_FALSE_QUESTIONS",
    "FILL_IN_THE_BLANKS",
    "IMPORTANT_QUESTIONS",
    "EXAM_PREPARATION",
    "FORMULA_SHEET",
    "CODE_EXPLANATION",
    "DOCUMENT_EXTRACTION",
    "STUDY_PLAN",
    "OTHER",
}

# Rule-based patterns for quick classification
RULE_PATTERNS = {
    "MCQ_GENERATION": [
        r"(?:prepare|generate|create|make|give)\s+(?:\d+\s+)?(?:mcq|multiple.?choice|objective)",
        r"mcq\b",
        r"multiple\s+choice\s+question",
    ],
    "QUIZ_MODE": [
        r"(?:quiz|test)\s+me",
        r"(?:start|begin|take)\s+(?:a\s+)?quiz",
    ],
    "TABLE_GENERATION": [
        r"(?:compare|comparison).*(?:table|tabular)",
        r"(?:in|as|make)\s+(?:a\s+)?table",
        r"tabular\s+form",
        r"table\s+of\s+",
    ],
    "COMPARISON": [
        r"compare\s+(?:and\s+contrast\s+)?",
        r"difference\s+between",
        r"vs\.?\s+",
        r"similarities\s+and\s+differences",
    ],
    "SUMMARIZATION": [
        r"summarize|summary|summarise",
        r"give\s+(?:me\s+)?(?:a\s+)?(?:brief|short)\s+",
        r"overview\s+of",
    ],
    "REVISION_NOTES": [
        r"revision\s+notes?",
        r"study\s+notes?",
        r"short\s+notes?",
        r"key\s+points?",
        r"important\s+points?",
    ],
    "STEP_BY_STEP_EXPLANATION": [
        r"step\s+by\s+step",
        r"explain\s+(?:the\s+)?(?:process|procedure|steps)",
        r"how\s+(?:to|does|do)",
        r"walk\s+(?:me\s+)?through",
    ],
    "CONCEPT_EXPLANATION": [
        r"(?:explain|what\s+is|define|describe)\s+",
        r"meaning\s+of",
        r"concept\s+of",
    ],
    "FLASHCARD_GENERATION": [
        r"flashcard",
        r"flash\s+card",
    ],
    "PRACTICE_PROBLEMS": [
        r"practice\s+(?:question|problem|exercise)",
        r"(?:solve|work\s+out)\s+",
        r"numerical\s+(?:problem|question)",
    ],
    "TRUE_FALSE_QUESTIONS": [
        r"true\s+(?:or|/)\s+false",
        r"true/false",
    ],
    "FILL_IN_THE_BLANKS": [
        r"fill\s+in\s+the\s+blank",
        r"fill\s+(?:in\s+)?(?:the\s+)?gaps?",
    ],
    "IMPORTANT_QUESTIONS": [
        r"important\s+question",
        r"(?:expected|likely|probable)\s+(?:exam\s+)?question",
        r"frequently\s+asked",
    ],
    "EXAM_PREPARATION": [
        r"exam\s+(?:prep|preparation|ready|oriented)",
        r"(?:prepare|ready)\s+(?:for|me\s+for)\s+(?:the\s+)?exam",
        r"mock\s+test",
        r"test\s+preparation",
    ],
    "FORMULA_SHEET": [
        r"formula\s+(?:sheet|list|table)",
        r"all\s+formula",
        r"list\s+(?:of\s+)?formula",
        r"important\s+formula",
    ],
    "CODE_EXPLANATION": [
        r"(?:explain|analyze|analyse)\s+(?:this\s+)?(?:code|program|algorithm)",
        r"code\s+(?:explanation|walkthrough)",
        r"what\s+does\s+this\s+code",
    ],
    "STUDY_PLAN": [
        r"study\s+plan",
        r"learning\s+(?:path|roadmap|plan)",
        r"how\s+(?:should|to)\s+(?:I\s+)?study",
    ],
}


class IntentDetectionService:
    """Detect the intent and desired output format of student queries."""

    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.gemini_generation_model
        self._compiled_patterns = {}

        # Compile regex patterns
        for intent, patterns in RULE_PATTERNS.items():
            self._compiled_patterns[intent] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    async def detect_intent(self, query: str) -> dict:
        """
        Detect the intent of a student query.

        Returns:
            dict with 'intent', 'format', and optional 'parameters'
        """
        # Try rule-based detection first
        rule_result = self._rule_based_detect(query)
        if rule_result:
            return rule_result

        # Fall back to LLM-based detection
        return await self._llm_based_detect(query)

    def _rule_based_detect(self, query: str) -> Optional[dict]:
        """Try to classify using regex patterns."""
        query_lower = query.lower().strip()

        for intent, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query_lower):
                    return {
                        "intent": intent,
                        "format": self._intent_to_format(intent),
                        "parameters": self._extract_parameters(query_lower, intent),
                    }

        return None

    async def _llm_based_detect(self, query: str) -> dict:
        """Use LLM to classify ambiguous queries."""
        prompt = f"""Classify the following student query into ONE intent category.

QUERY: {query}

CATEGORIES:
- QUESTION_ANSWERING: Direct question about a topic
- MCQ_GENERATION: Request to create multiple-choice questions
- QUIZ_MODE: Request for an interactive quiz
- TABLE_GENERATION: Request to present information in a table
- COMPARISON: Request to compare two or more items
- SUMMARIZATION: Request for a summary
- REVISION_NOTES: Request for study/revision notes
- STEP_BY_STEP_EXPLANATION: Request for step-by-step breakdown
- CONCEPT_EXPLANATION: Request to explain a concept
- FLASHCARD_GENERATION: Request for flashcards
- PRACTICE_PROBLEMS: Request for practice questions
- TRUE_FALSE_QUESTIONS: Request for true/false questions
- FILL_IN_THE_BLANKS: Request for fill-in-the-blank questions
- IMPORTANT_QUESTIONS: Request for important/likely exam questions
- EXAM_PREPARATION: Request for exam preparation material
- FORMULA_SHEET: Request for formula compilation
- CODE_EXPLANATION: Request to explain code
- STUDY_PLAN: Request for a study plan
- OTHER: None of the above

Respond with ONLY a JSON object (no markdown):
{{"intent": "CATEGORY_NAME", "count": null_or_number_if_requested}}"""

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=128,
                ),
            )

            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text
                text = text.rsplit("```", 1)[0]

            data = json.loads(text.strip())
            intent = data.get("intent", "QUESTION_ANSWERING")

            if intent not in INTENTS:
                intent = "QUESTION_ANSWERING"

            return {
                "intent": intent,
                "format": self._intent_to_format(intent),
                "parameters": {"count": data.get("count")},
            }

        except Exception as e:
            logger.warning(f"LLM intent detection failed: {e}")
            return {
                "intent": "QUESTION_ANSWERING",
                "format": "text",
                "parameters": {},
            }

    def _intent_to_format(self, intent: str) -> str:
        """Map intent to response format."""
        format_map = {
            "QUESTION_ANSWERING": "text",
            "MCQ_GENERATION": "interactive_quiz",
            "QUIZ_MODE": "interactive_quiz",
            "TABLE_GENERATION": "table",
            "COMPARISON": "table",
            "SUMMARIZATION": "summary",
            "REVISION_NOTES": "summary",
            "STEP_BY_STEP_EXPLANATION": "step_by_step",
            "CONCEPT_EXPLANATION": "text",
            "FLASHCARD_GENERATION": "flashcards",
            "PRACTICE_PROBLEMS": "interactive_quiz",
            "TRUE_FALSE_QUESTIONS": "interactive_quiz",
            "FILL_IN_THE_BLANKS": "interactive_quiz",
            "IMPORTANT_QUESTIONS": "text",
            "EXAM_PREPARATION": "text",
            "FORMULA_SHEET": "table",
            "CODE_EXPLANATION": "code",
            "STUDY_PLAN": "text",
            "OTHER": "text",
        }
        return format_map.get(intent, "text")

    def _extract_parameters(self, query: str, intent: str) -> dict:
        """Extract relevant parameters from the query."""
        params = {}

        # Extract count/number
        count_match = re.search(r'(\d+)\s+(?:mcq|question|flashcard|problem)', query)
        if count_match:
            params["count"] = int(count_match.group(1))

        # Extract difficulty
        if "easy" in query:
            params["difficulty"] = "easy"
        elif "hard" in query or "difficult" in query:
            params["difficulty"] = "hard"
        elif "medium" in query:
            params["difficulty"] = "medium"

        return params
