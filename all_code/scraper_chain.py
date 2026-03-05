"""
scrapers/scraper_chain.py
─────────────────────────
Tries each scraper in SCRAPER_CHAIN order.
Returns the first non-empty text or None if all fail.

Fallback order:
  requests → cloudscraper → crawl4ai → curl_cffi
  → playwright → scrapy → selenium
"""

import logging
import asyncio
from typing import Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Shared HTML → clean text helper
# ─────────────────────────────────────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "svg", "form"]):
        tag.decompose()
    text  = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines()]
    return "\n".join(l for l in lines if l)


# ─────────────────────────────────────────────────────────────────────────────
# Individual scrapers (each returns str | None)
# ─────────────────────────────────────────────────────────────────────────────

def _scrape_requests(url: str) -> Optional[str]:
    """Standard requests + BeautifulSoup."""
    try:
        import requests
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            text = _html_to_text(r.text)
            if text:
                return text
        logger.debug(f"[requests] status={r.status_code} for {url}")
    except Exception as e:
        logger.debug(f"[requests] failed: {e}")
    return None


def _scrape_cloudscraper(url: str) -> Optional[str]:
    """cloudscraper – bypasses basic Cloudflare JS challenges."""
    try:
        import cloudscraper
        scraper = cloudscraper.create_scraper()
        r = scraper.get(url, timeout=20)
        if r.status_code == 200:
            text = _html_to_text(r.text)
            if text:
                return text
        logger.debug(f"[cloudscraper] status={r.status_code} for {url}")
    except Exception as e:
        logger.debug(f"[cloudscraper] failed: {e}")
    return None


def _scrape_crawl4ai(url: str) -> Optional[str]:
    """crawl4ai async crawler – returns markdown."""
    try:
        from crawl4ai import AsyncWebCrawler

        async def _run():
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(
                    url=url,
                    word_count_threshold=10,
                    bypass_cache=True
                )
                return result.markdown or ""

        text = asyncio.run(_run()).strip()
        if text:
            return text
        logger.debug(f"[crawl4ai] empty result for {url}")
    except Exception as e:
        logger.debug(f"[crawl4ai] failed: {e}")
    return None


def _scrape_curl_cffi(url: str) -> Optional[str]:
    """curl_cffi – impersonates Chrome TLS fingerprint."""
    try:
        from curl_cffi import requests as cffi_requests
        r = cffi_requests.get(url, impersonate="chrome110", timeout=30)
        if r.status_code == 200:
            text = _html_to_text(r.text)
            if text:
                return text
        logger.debug(f"[curl_cffi] status={r.status_code} for {url}")
    except Exception as e:
        logger.debug(f"[curl_cffi] failed: {e}")
    return None


def _scrape_playwright(url: str) -> Optional[str]:
    """Playwright headless Chromium – full JS rendering."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page    = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_load_state("networkidle")
            html = page.content()
            browser.close()
        text = _html_to_text(html)
        if text:
            return text
        logger.debug(f"[playwright] empty result for {url}")
    except Exception as e:
        logger.debug(f"[playwright] failed: {e}")
    return None


def _scrape_scrapy(url: str) -> Optional[str]:
    """Scrapy one-off spider."""
    try:
        import scrapy
        from scrapy.crawler import CrawlerProcess

        result_bucket = []

        class _OneShot(scrapy.Spider):
            name = "one_shot"
            start_urls = [url]

            def parse(self, response):
                text = _html_to_text(response.text)
                if text:
                    result_bucket.append(text)

        process = CrawlerProcess(settings={
            "USER_AGENT": "Mozilla/5.0",
            "LOG_ENABLED": False,
        })
        process.crawl(_OneShot)
        process.start()

        if result_bucket:
            return result_bucket[0]
        logger.debug(f"[scrapy] empty result for {url}")
    except Exception as e:
        logger.debug(f"[scrapy] failed: {e}")
    return None


def _scrape_selenium(url: str) -> Optional[str]:
    """Selenium + undetected ChromeDriver."""
    try:
        import undetected_chromedriver as uc
        import time

        driver = uc.Chrome(headless=True)
        driver.get(url)
        time.sleep(5)
        html = driver.page_source
        driver.quit()
        text = _html_to_text(html)
        if text:
            return text
        logger.debug(f"[selenium] empty result for {url}")
    except Exception as e:
        logger.debug(f"[selenium] failed: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Registry
# ─────────────────────────────────────────────────────────────────────────────

_SCRAPERS = {
    "requests":     _scrape_requests,
    "cloudscraper": _scrape_cloudscraper,
    "crawl4ai":     _scrape_crawl4ai,
    "curl_cffi":    _scrape_curl_cffi,
    "playwright":   _scrape_playwright,
    "scrapy":       _scrape_scrapy,
    "selenium":     _scrape_selenium,
}


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

def scrape_with_fallback(url: str, chain: list = None) -> Optional[str]:
    """
    Try each scraper in *chain* order.
    Returns the first successful text or None.

    Args:
        url:   Target URL.
        chain: Ordered list of scraper keys.  Defaults to SCRAPER_CHAIN
               from settings if not provided.
    """
    if chain is None:
        from config.settings import SCRAPER_CHAIN
        chain = SCRAPER_CHAIN

    for name in chain:
        scraper_fn = _SCRAPERS.get(name)
        if not scraper_fn:
            logger.warning(f"Unknown scraper '{name}' – skipping.")
            continue

        logger.info(f"[{name}] attempting {url}")
        try:
            text = scraper_fn(url)
            if text:
                logger.info(f"[{name}] ✓ success ({len(text):,} chars) for {url}")
                return text
        except Exception as e:
            logger.warning(f"[{name}] ✗ error: {e}")

    logger.error(f"All scrapers failed for {url}")
    return None
