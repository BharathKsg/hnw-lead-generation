"""
pipeline/orchestrator.py
────────────────────────
Full HNW lead-generation pipeline.

Flow:
  1. Tavily  →  list of URLs
  2. ThreadPoolExecutor(SCRAPE_THREADS)  →  scrape each URL with fallback chain
  3. MarkdownTextSplitter  →  chunks (10 000 / 500)
  4. ThreadPoolExecutor(ANALYSIS_THREADS) →  Azure LLM analyses every chunk
  5. Deduplicate leads by (full_name, city)
  6. Filter by MIN_HNW_SCORE / MIN_NET_WORTH_MILLION
  7. Upsert into MongoDB
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from config.settings import (
    TAVILY_API_KEY,
    TARGET_CITY,
    SCRAPE_THREADS, ANALYSIS_THREADS,
    MIN_HNW_SCORE, MIN_NET_WORTH_MILLION,
    MAX_LEADS_PER_RUN, REQUEST_DELAY,
    SCRAPER_CHAIN,
)
from lib.search   import HNWISearchService
from lib.chunker  import chunk_text
from lib.llm      import AzureAnalyser
from lib.db       import LeadStore
from scrapers.scraper_chain import scrape_with_fallback

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Step helpers
# ─────────────────────────────────────────────────────────────────────────────

def _scrape_one(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Scrape a single URL through the fallback chain.
    Returns the item dict augmented with 'raw_text' (str | None).
    """
    url  = item["url"]
    text = scrape_with_fallback(url, chain=SCRAPER_CHAIN)
    if text:
        logger.info(f"[scrape] ✓ {url}  ({len(text):,} chars)")
    else:
        logger.warning(f"[scrape] ✗ all scrapers failed for {url}")
    return {**item, "raw_text": text}


def _analyse_chunk(
    chunk: str,
    source_url: str,
    analyser: AzureAnalyser,
    city: str,
) -> List[Dict]:
    """
    Send one chunk to the LLM and return a flat list of lead dicts.
    """
    raw = analyser.analyse_chunk(
        chunk=chunk,
        source_url=source_url,
        city=city,
    )
    leads = []
    for key, lead in raw.items():
        if isinstance(lead, dict) and lead.get("full_name"):
            leads.append(lead)
    return leads


# def _qualify_lead(lead: Dict, min_score: int, min_worth_m: float) -> bool:
#     """Return True if lead passes minimum thresholds."""
#     score = lead.get("overall_hni_score", 0) or 0
#     worth = lead.get("net_worth", 0) or 0
#     currency = lead.get("net_worth_currency", "USD")

#     # Convert net worth to millions USD for comparison
#     worth_m = worth / 1_000_000
#     if currency == "INR":
#         worth_m = worth / 83_000_000   # approx 1 USD = 83 INR, express in M USD

#     return score >= min_score and worth_m >= min_worth_m


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class HNWPipeline:
    def __init__(self, city: str = TARGET_CITY):
        self.city = city
        self.search_svc = HNWISearchService(api_key=TAVILY_API_KEY)
        self.analyser   = AzureAnalyser()
        self.db         = LeadStore()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> List[Dict]:
        logger.info(f"═══ HNW Pipeline start | city={self.city} ═══")
        t0 = time.time()
        print(f"Running HNWPipeline for city: {self.city}")
        # 1. Discover URLs via Tavily
        url_items = self.search_svc.search_hnwi(self.city)
        logger.info(f"[search] {len(url_items)} URLs to process")
        print("url_itemsurl_itemsurl_itemsurl_items",url_items)
        if not url_items:
            logger.warning("[search] no URLs found – aborting.")
            return []
#         url_items = data = [
#     {
#         "title": "Top 10 Richest Person In Meghalaya 2025 Exclusive List",
#         "url": "https://skillcircle.in/top-10-richest-person-in-meghalaya/",
#         "content": "Conrad Sangma has the most money in Meghalaya. He leads the state as Chief Minister and is part of a powerful political family. Read more",
#         "score": 0
#     }
# ]
        # 2. Scrape URLs in parallel (SCRAPE_THREADS workers)
        scraped_items = self._parallel_scrape(url_items)

        # 3. Chunk + Analyse in parallel (ANALYSIS_THREADS workers)
        all_leads = self._parallel_analyse(scraped_items)
        print("all_leadsall_leadsall_leadsall_leads",all_leads)
        # 4. Deduplicate across chunks
        # all_leads = self._deduplicate(all_leads)
        # logger.info(f"[dedup] {len(all_leads)} unique leads")

        # 5. Filter by score / net worth
        # qualified = [
        #     l for l in all_leads
        #     if _qualify_lead(l, MIN_HNW_SCORE, MIN_NET_WORTH_MILLION)
        # ]
        # qualified = qualified[:MAX_LEADS_PER_RUN]
        # logger.info(f"[filter] {len(qualified)} leads meet thresholds")

        # 6. Store in MongoDB
        if all_leads:
            stored = self.db.upsert_leads(all_leads)
            logger.info(f"[db] {stored} documents upserted/updated")

        elapsed = time.time() - t0
        logger.info(f"═══ Pipeline complete in {elapsed:.1f}s | {len(all_leads)} leads saved ═══")
        self.db.close()
        return all_leads

    # ── Step 2: parallel scraping ─────────────────────────────────────────────

    def _parallel_scrape(self, url_items: List[Dict]) -> List[Dict]:
        results = []
        with ThreadPoolExecutor(max_workers=SCRAPE_THREADS) as pool:
            futures = {pool.submit(_scrape_one, item): item for item in url_items}
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result.get("raw_text"):
                        results.append(result)
                    time.sleep(REQUEST_DELAY)   # polite delay per completed task
                except Exception as e:
                    logger.error(f"[scrape] unexpected error: {e}")
        logger.info(f"[scrape] {len(results)}/{len(url_items)} URLs successfully scraped")
        return results

    # ── Step 3+4: parallel chunk → LLM analysis ───────────────────────────────

    def _parallel_analyse(self, scraped_items: List[Dict]) -> List[Dict]:
        # Build all (chunk, source_url) pairs first
        chunk_tasks = []
        for item in scraped_items:
            text = item.get("raw_text", "")
            if not text:
                continue
            url    = item["url"]
            chunks = chunk_text(text)
            logger.info(f"[chunk] {url}  → {len(chunks)} chunks")
            for c in chunks:
                chunk_tasks.append((c, url))

        logger.info(f"[analysis] {len(chunk_tasks)} chunks to analyse")

        all_leads: List[Dict] = []
        with ThreadPoolExecutor(max_workers=ANALYSIS_THREADS) as pool:
            futures = {
                pool.submit(
                    _analyse_chunk, chunk, url,
                    self.analyser, self.city
                ): (chunk, url)
                for chunk, url in chunk_tasks
            }
            for future in as_completed(futures):
                try:
                    leads = future.result()
                    all_leads.extend(leads)
                    if leads:
                        logger.debug(f"[analysis] found {len(leads)} lead(s) in chunk")
                except Exception as e:
                    logger.error(f"[analysis] error: {e}")

        logger.info(f"[analysis] {len(all_leads)} raw leads extracted")
        return all_leads

    # ── Deduplication ─────────────────────────────────────────────────────────

    @staticmethod
    def _deduplicate(leads: List[Dict]) -> List[Dict]:
        """
        Keep highest overall_hni_score per (full_name, city).
        """
        best: Dict[tuple, Dict] = {}
        for lead in leads:
            name = (lead.get("full_name") or "").strip().lower()
            city = (lead.get("city") or "").strip().lower()
            if not name:
                continue
            key   = (name, city)
            score = lead.get("overall_hni_score", 0) or 0
            if key not in best or score > (best[key].get("overall_hni_score", 0) or 0):
                best[key] = lead
        return list(best.values())