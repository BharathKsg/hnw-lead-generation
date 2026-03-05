"""
lib/search.py
─────────────
Tavily-based HNWI URL discovery.
Returns a deduplicated list of {title, url, content, score} dicts.
"""

import os
import json
import logging
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from config.settings import BLOCKED_DOMAINS

logger = logging.getLogger(__name__)


def _is_blocked(url: str) -> bool:
    """Return True if the URL belongs to a domain we cannot scrape."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in BLOCKED_DOMAINS)


class HNWISearchService:

    QUERY_TEMPLATES = [
        '"{city}" richest people net worth billionaire millionaire',
        # '"{city}" wealthiest celebrity entrepreneur founder',
        # '"{city}" IPO founder billionaire millionaire wealth',
        # '"{city}" high net worth CEO founder entrepreneur',
        # '"{city}" top businessmen investors wealth of the year',
    ]

    def __init__(self, api_key: str, max_results: int = 10):
        from langchain_community.tools.tavily_search import TavilySearchResults
        self.search = TavilySearchResults(
            tavily_api_key=api_key,
            max_results=max_results,
            search_depth="advanced",
        )

    def build_queries(self, city: str) -> List[str]:
        return [t.format(city=city) for t in self.QUERY_TEMPLATES]

    def execute_search(self, query: str) -> List[Dict[str, Any]]:
        try:
            logger.info(f"[Tavily] searching: {query}")
            return self.search.invoke(query)
        except Exception as e:
            logger.error(f"[Tavily] failed: {e}")
            return []

    def search_hnwi(self, city: str) -> List[Dict[str, Any]]:
        queries = self.build_queries(city)
        seen: set  = set()   # global URL set across ALL queries
        unique: List[Dict[str, Any]] = []

        for q in queries:
            results  = self.execute_search(q)
            new_this = 0
            skip_this = 0
            for r in results:
                url = r.get("url", "").strip()
                if not url:
                    continue
                if url in seen:
                    skip_this += 1
                    logger.debug(f"[Tavily] duplicate URL skipped: {url}")
                    continue
                if _is_blocked(url):
                    skip_this += 1
                    logger.info(f"[Tavily] blocked domain skipped: {url}")
                    continue
                seen.add(url)
                new_this += 1
                unique.append({
                    "title":   r.get("title", ""),
                    "url":     url,
                    "content": r.get("content", ""),
                    "score":   r.get("score", 0),
                })
            logger.info(
                f"[Tavily] query '{q[:60]}…' → {new_this} new, {skip_this} duplicate URLs skipped"
            )

        logger.info(f"[Tavily] {len(unique)} unique URLs total for '{city}'")
        return unique