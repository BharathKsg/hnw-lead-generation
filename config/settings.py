# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR    = BASE_DIR / "logs"
OUTPUT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ── Azure OpenAI ──────────────────────────────────────────────────────────────
AZURE_OPENAI_ENDPOINT= os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY= os.getenv("AZURE_OPENAI_API_KEY",  "")
AZURE_OPENAI_DEPLOYMENT= os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
AZURE_OPENAI_API_VERSION= os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")

# ── Search APIs ───────────────────────────────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME    = os.getenv("MONGO_DB_NAME",    "hnw_leads")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "leads")

# ── Location ──────────────────────────────────────────────────────────────────
TARGET_CITY = os.getenv("TARGET_CITY", "Bangalore")

# ── Pipeline ──────────────────────────────────────────────────────────────────
MIN_HNW_SCORE         = int(os.getenv("MIN_HNW_SCORE",          "60"))
MIN_NET_WORTH_MILLION = float(os.getenv("MIN_NET_WORTH_MILLION", "5"))
MAX_LEADS_PER_RUN     = int(os.getenv("MAX_LEADS_PER_RUN",      "150"))
REQUEST_DELAY         = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5"))

# ── Threading ─────────────────────────────────────────────────────────────────
# Number of URLs scraped in parallel
SCRAPE_THREADS    = int(os.getenv("SCRAPE_THREADS",    "5"))
# Number of chunks processed (LLM) in parallel
ANALYSIS_THREADS  = int(os.getenv("ANALYSIS_THREADS",  "5"))

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = int(os.getenv("CHUNK_SIZE",    "10000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "500"))

# ── Scraper fallback order ────────────────────────────────────────────────────
# Each entry is a scraper key; the pipeline tries them left-to-right
SCRAPER_CHAIN = [
    "requests",       # general_scrape  (fastest, no overhead)
    "cloudscraper",   # bypass basic Cloudflare JS challenges
    "crawl4ai",       # async AI-aware crawler
    "curl_cffi",      # impersonates real Chrome TLS fingerprint
    "playwright",     # full headless browser
    "scrapy",         # Scrapy spider
    "selenium",       # Selenium + ChromeDriver
]

# ── HNW categories ────────────────────────────────────────────────────────────
HNW_CATEGORIES = [
    "celebrity", "billionaire", "millionaire",
    "business owner", "company founder", "CEO",
    "Managing Director", "President", "entrepreneur",
    "investor", "real estate developer", "tech founder",
    "film director", "actor", "musician", "sports star",
    "hedge fund manager", "venture capitalist",
]

TRIGGER_KEYWORDS = {
    "ACQUISITION":      ["acqui", "merger", "takeover"],
    "IPO":              ["ipo", "initial public offering", "went public"],
    "PE_INVESTMENT":    ["private equity", "growth equity", "buyout"],
    "BUSINESS_SALE":    ["sold company", "sale of", "divested"],
    "RECAPITALIZATION": ["recapitali", "dividend recap"],
    "SUCCESSION":       ["succession", "next generation", "transition"],
    "REAL_ESTATE":      ["real estate portfolio", "commercial real estate"],
    "PHILANTHROPY":     ["philanthrop", "foundation", "endowment"],
    "FUNDING":          ["raised", "series a", "series b", "series c"],
    "CELEBRITY_DEAL":   ["brand deal", "endorsement", "signed with", "record deal"],
}