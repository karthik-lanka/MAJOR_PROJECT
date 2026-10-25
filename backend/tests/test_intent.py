"""
Unit tests for intent detection service.
"""

import pytest
from app.services.intent_detection import IntentDetectionService


@pytest.mark.asyncio
async def test_mcq_intent_detection():
    service = IntentDetectionService()
    result = await service.detect_intent("Create 5 MCQs on Operating Systems scheduling algorithms")
    assert result["intent"] == "MCQ_GENERATION"
    assert result["format"] == "interactive_quiz"


@pytest.mark.asyncio
async def test_quiz_intent_detection():
    service = IntentDetectionService()
    result = await service.detect_intent("Quiz me on compiler design")
    assert result["intent"] == "QUIZ_MODE"
    assert result["format"] == "interactive_quiz"


@pytest.mark.asyncio
async def test_table_intent_detection():
    service = IntentDetectionService()
    result = await service.detect_intent("Compare TCP and UDP in a table format")
    assert result["intent"] in ("TABLE_GENERATION", "COMPARISON")
    assert result["format"] in ("table", "markdown")


@pytest.mark.asyncio
async def test_summary_intent_detection():
    service = IntentDetectionService()
    result = await service.detect_intent("Give me a brief summary of chapter 3")
    assert result["intent"] == "SUMMARIZATION"
    assert result["format"] == "summary"


@pytest.mark.asyncio
async def test_flashcard_intent_detection():
    service = IntentDetectionService()
    result = await service.detect_intent("Make flashcards for key machine learning terms")
    assert result["intent"] == "FLASHCARD_GENERATION"
    assert result["format"] == "flashcards"
