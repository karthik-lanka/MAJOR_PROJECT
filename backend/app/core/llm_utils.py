"""
Resilient LLM call utility with retry and exponential backoff.
Handles transient 503 (high demand) and 429 (rate limit) errors.
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


async def generate_content_with_retry(
    client,
    model: str,
    contents,
    config=None,
    max_retries: int = 3,
    initial_delay: float = 1.5,
):
    """Call Gemini generate_content with automatic retry on transient errors."""
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries):
        try:
            return await asyncio.to_thread(
                client.models.generate_content,
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            err_str = str(e)
            is_transient = "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "RESOURCE_EXHAUSTED" in err_str
            last_error = e

            if is_transient and attempt < max_retries - 1:
                logger.warning(
                    f"Transient Gemini error (attempt {attempt + 1}/{max_retries}): {err_str[:120]}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay *= 2.0
            else:
                logger.error(f"Gemini call failed (attempt {attempt + 1}/{max_retries}): {err_str[:160]}")
                raise e

    raise last_error
