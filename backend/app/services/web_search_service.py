"""
Web search service abstraction.
Supports Google Custom Search API with fallback capability.
"""

import asyncio
import logging
from typing import Optional
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    """A single web search result."""
    title: str
    url: str
    snippet: str
    source: str = ""
    date: Optional[str] = None


class WebSearchService:
    """Web search abstraction supporting multiple providers."""

    def __init__(self):
        settings = get_settings()
        self.provider = settings.web_search_provider
        self.api_key = settings.web_search_api_key
        self.cse_id = settings.google_cse_id

    @property
    def is_configured(self) -> bool:
        """Check if web search is properly configured."""
        if self.provider == "google":
            return bool(self.api_key and self.cse_id)
        return bool(self.api_key and self.provider)

    async def search(
        self,
        query: str,
        num_results: int = 5,
    ) -> list[WebSearchResult]:
        """
        Search the web for relevant information.
        Returns a list of search results.
        """
        if not self.is_configured:
            logger.warning("Web search not configured")
            return []

        if self.provider == "google":
            return await self._google_search(query, num_results)
        else:
            logger.warning(f"Unsupported search provider: {self.provider}")
            return []

    async def _google_search(
        self, query: str, num_results: int
    ) -> list[WebSearchResult]:
        """Search using Google Custom Search API."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.api_key,
                        "cx": self.cse_id,
                        "q": query,
                        "num": min(num_results, 10),
                    },
                )
                response.raise_for_status()
                data = response.json()

            results = []
            for item in data.get("items", []):
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source="google",
                ))

            logger.info(f"Web search returned {len(results)} results for: {query[:50]}")
            return results

        except httpx.TimeoutException:
            logger.error("Web search timed out")
            return []
        except httpx.HTTPStatusError as e:
            logger.error(f"Web search HTTP error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return []

    def format_results_as_context(self, results: list[WebSearchResult]) -> str:
        """Format search results as context for the LLM."""
        if not results:
            return ""

        parts = []
        for i, result in enumerate(results, 1):
            parts.append(
                f"[Web Source {i}] {result.title}\n"
                f"URL: {result.url}\n"
                f"{result.snippet}"
            )

        return "\n\n---\n\n".join(parts)
