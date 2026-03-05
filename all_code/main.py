"""
main.py
───────
Entry point for the HNW Lead Generation Pipeline.

Usage:
    python main.py
    python main.py --city Mumbai --state Maharashtra --country India
    python main.py --city "New York" --state "New York" --country "United States"
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# ── Logging setup (before any imports that use the logger) ───────────────────
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            LOG_DIR / f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            encoding="utf-8",
        ),
    ],
)

# Silence noisy third-party loggers
for noisy in ("urllib3", "httpx", "httpcore", "openai", "scrapy", "twisted"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ── Pipeline import (after logging is configured) ────────────────────────────
from pipeline.orchestrator import HNWPipeline
from config.settings import TARGET_CITY


def parse_args():
    parser = argparse.ArgumentParser(description="HNW Lead Generation Pipeline")
    parser.add_argument("--city", default=TARGET_CITY, help="Target city (e.g. Bangalore, Mumbai, Dubai)")
    return parser.parse_args()


def main():
    args = parse_args()

    logger.info(f"Starting pipeline for city: {args.city}")

    pipeline = HNWPipeline(city=args.city)
    leads = pipeline.run()
    
    # Save a JSON snapshot of this run
    output_path = Path("output") / f"leads_{args.city.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved to {output_path}")
    logger.info(f"Total qualified leads: {len(leads)}")

    # Print summary table to stdout
    if leads:
        print("\n" + "═" * 90)
        print(f"{'#':<4} {'Name':<30} {'Category':<22} {'Score':>5}  {'Net Worth':>14}  {'Status'}")
        print("─" * 90)
        for i, l in enumerate(leads, 1):
            nw  = l.get("net_worth", 0) or 0
            cur = l.get("net_worth_currency", "")



if __name__ == "__main__":
    main()