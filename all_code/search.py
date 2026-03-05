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

logger = logging.getLogger(__name__)


class HNWISearchService:

    QUERY_TEMPLATES = [
        '"{city}" richest people net worth billionaire millionaire',
        '"{city}" wealthiest celebrity entrepreneur founder',
        '"{city}" IPO founder billionaire millionaire wealth',
        '"{city}" high net worth CEO founder entrepreneur',
        '"{city}" top businessmen investors wealth of the year',
    ]

    def __init__(self, api_key: str, max_results: int = 5):
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
        queries     = self.build_queries(city)
        all_results = []
        for q in queries:
            all_results.extend(self.execute_search(q))

        # deduplicate by URL
        seen, unique = set(), []
        for r in all_results:
            url = r.get("url", "")
            if url and url not in seen:
                seen.add(url)
                unique.append({
                    "title":   r.get("title", ""),
                    "url":     url,
                    "content": r.get("content", ""),
                    "score":   r.get("score", 0),
                })

        logger.info(f"[Tavily] {len(unique)} unique URLs found for {city}")
        return unique