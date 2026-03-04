# HNW Lead Generation Pipeline

Automated pipeline to discover, scrape, analyse, and store **High Net Worth Individual** leads for a target location.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          main.py  (CLI entry)                           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   HNWPipeline.run()      │
                    │  pipeline/orchestrator   │
                    └────────────┬────────────┘
                                 │
          ┌──────────────────────▼──────────────────────┐
          │  STEP 1 – Tavily Search (lib/search.py)      │
          │  6 query templates × location                │
          │  → deduplicated list of URLs                 │
          └──────────────────────┬──────────────────────┘
                                 │  N URLs
          ┌──────────────────────▼──────────────────────┐
          │  STEP 2 – Parallel Scraping                  │
          │  ThreadPoolExecutor(SCRAPE_THREADS=5)        │
          │                                              │
          │  Per URL → scraper_chain.scrape_with_fallback│
          │  ┌──────────────────────────────────────┐   │
          │  │ 1. requests + BeautifulSoup           │   │
          │  │    ↓ fail                             │   │
          │  │ 2. cloudscraper (Cloudflare bypass)   │   │
          │  │    ↓ fail                             │   │
          │  │ 3. crawl4ai (async AI crawler)        │   │
          │  │    ↓ fail                             │   │
          │  │ 4. curl_cffi (Chrome TLS fingerprint) │   │
          │  │    ↓ fail                             │   │
          │  │ 5. playwright (headless Chromium)     │   │
          │  │    ↓ fail                             │   │
          │  │ 6. scrapy (spider)                    │   │
          │  │    ↓ fail                             │   │
          │  │ 7. selenium / undetected-chromedriver │   │
          │  └──────────────────────────────────────┘   │
          └──────────────────────┬──────────────────────┘
                                 │  raw text per URL
          ┌──────────────────────▼──────────────────────┐
          │  STEP 3 – Chunking (lib/chunker.py)          │
          │  MarkdownTextSplitter                        │
          │  chunk_size=10 000  chunk_overlap=500        │
          └──────────────────────┬──────────────────────┘
                                 │  chunks[]
          ┌──────────────────────▼──────────────────────┐
          │  STEP 4 – Parallel LLM Analysis              │
          │  ThreadPoolExecutor(ANALYSIS_THREADS=5)      │
          │  Azure OpenAI GPT-4 (JSON mode)              │
          │  → list of lead dicts per chunk              │
          └──────────────────────┬──────────────────────┘
                                 │
          ┌──────────────────────▼──────────────────────┐
          │  STEP 5 – Deduplication                      │
          │  key = (full_name.lower(), city.lower())     │
          │  keep highest overall_hni_score              │
          └──────────────────────┬──────────────────────┘
                                 │
          ┌──────────────────────▼──────────────────────┐
          │  STEP 6 – Qualification Filter               │
          │  overall_hni_score ≥ MIN_HNW_SCORE (60)     │
          │  net_worth ≥ MIN_NET_WORTH_MILLION (5 M USD) │
          └──────────────────────┬──────────────────────┘
                                 │
          ┌──────────────────────▼──────────────────────┐
          │  STEP 7 – MongoDB Upsert (lib/db.py)         │
          │  upsert on (full_name, city)                 │
          │  JSON snapshot saved to output/              │
          └─────────────────────────────────────────────┘
```

---

## Project Structure

```
hnw_pipeline/
├── main.py                     ← CLI entry point
├── requirements.txt
├── .env.example                ← copy to .env and fill in
│
├── config/
│   └── settings.py             ← all env-driven config
│
├── lib/
│   ├── search.py               ← Tavily URL discovery
│   ├── chunker.py              ← MarkdownTextSplitter
│   ├── llm.py                  ← Azure OpenAI analyser
│   └── db.py                   ← MongoDB upsert / query
│
├── scrapers/
│   └── scraper_chain.py        ← 7-scraper fallback chain
│
├── pipeline/
│   └── orchestrator.py         ← ThreadPoolExecutor orchestration
│
├── output/                     ← JSON snapshots per run
└── logs/                       ← timestamped log files
```

---

## Setup

```bash
# 1. Clone / copy the project
cd hnw_pipeline

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browser
playwright install chromium

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys and MongoDB URI

# 6. Run
python main.py                                         # uses .env defaults
python main.py --city Mumbai --state Maharashtra       # override location
python main.py --city "New York" --country "United States"
```

---

## Key Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SCRAPE_THREADS` | `5` | Parallel URL scrapers |
| `ANALYSIS_THREADS` | `5` | Parallel LLM chunk analysers |
| `CHUNK_SIZE` | `10000` | Markdown chunk size (chars) |
| `CHUNK_OVERLAP` | `500` | Chunk overlap (chars) |
| `MIN_HNW_SCORE` | `60` | Minimum HNI score to store |
| `MIN_NET_WORTH_MILLION` | `5` | Minimum net worth (millions USD) |
| `MAX_LEADS_PER_RUN` | `150` | Cap on leads stored per run |

---

## Scraper Fallback Order

The chain is defined in `SCRAPER_CHAIN` (settings.py) and tried **in order** for every URL:

1. `requests` — fastest, no overhead
2. `cloudscraper` — bypasses basic Cloudflare JS challenges
3. `crawl4ai` — async AI-aware crawler
4. `curl_cffi` — impersonates real Chrome TLS fingerprint
5. `playwright` — full headless Chromium
6. `scrapy` — Scrapy spider
7. `selenium` — undetected ChromeDriver

You can reorder or remove entries from `SCRAPER_CHAIN` in `.env` / `settings.py`.

---

## MongoDB Schema

Each document in `hnw_leads.leads` contains all 40+ fields from the LLM prompt, plus:

- `source_url` — where the lead was found
- `created_at` / `updated_at` — ISO timestamps
- Unique index on `(full_name, city)`
