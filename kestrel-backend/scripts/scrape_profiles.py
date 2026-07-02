"""Batch scrape company profiles from MOPS (TW) and Yahoo Finance (US).

Stores results in data/company_profiles.json.
Run weekly to keep profiles current.

Usage: python -m scripts.scrape_profiles [--tw] [--us]
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.logging import get_logger
from app.providers.yfinance import YFinanceProvider
from app.scrapers.mops_profile import MOPSProfileScraper

logger = get_logger(__name__)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "company_profiles.json"

# Top TW stocks to scrape
TW_STOCKS = [
    "2330", "2317", "2454", "2382", "2308", "3711", "2412", "2881", "2882", "2303",
    "3231", "2886", "2891", "1301", "2002", "3034", "2884", "6505", "2357", "2603",
    "3008", "2345", "2327", "3481", "2344", "2376", "2409", "2912", "1303", "5880",
]

# Top US stocks to scrape
US_STOCKS = [
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "TSM", "AVGO", "AMD",
]


async def scrape_tw_profiles() -> list[dict]:
    """Scrape TW stock profiles from MOPS."""
    scraper = MOPSProfileScraper()
    profiles = []

    for stock_id in TW_STOCKS:
        logger.info("scraping_tw", stock_id=stock_id)
        profile = await scraper.get_company_info(stock_id)
        if not profile.get("error"):
            profiles.append(profile)
        await asyncio.sleep(2)  # Rate limit: be polite to MOPS

    return profiles


async def scrape_us_profiles() -> list[dict]:
    """Fetch US stock profiles via yfinance API."""
    provider = YFinanceProvider()
    profiles = []

    for ticker in US_STOCKS:
        logger.info("fetching_us", ticker=ticker)
        profile = await provider.get_info(ticker)
        if not profile.get("error"):
            profiles.append(profile)
        await asyncio.sleep(0.5)

    return profiles


async def scrape_batch(stock_ids: list[str], delay: float = 2.0) -> list[dict]:
    """Scrape a small batch of TW stocks. Used by tests."""
    scraper = MOPSProfileScraper()
    results = []
    for stock_id in stock_ids:
        profile = await scraper.get_company_info(stock_id)
        results.append(profile)
        if len(stock_ids) > 1:
            await asyncio.sleep(delay)
    return results


async def main():
    tw_flag = "--tw" in sys.argv or len(sys.argv) == 1
    us_flag = "--us" in sys.argv or len(sys.argv) == 1

    # Load existing profiles
    existing = []
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH, encoding="utf-8") as f:
            existing = json.load(f)

    new_profiles = []

    if tw_flag:
        tw = await scrape_tw_profiles()
        new_profiles.extend(tw)
        logger.info("tw_profiles_scraped", count=len(tw))

    if us_flag:
        us = await scrape_us_profiles()
        new_profiles.extend(us)
        logger.info("us_profiles_scraped", count=len(us))

    # Merge: update existing, add new
    merged_map = {p.get("stock_id") or p.get("ticker"): p for p in existing}
    for p in new_profiles:
        key = p.get("stock_id") or p.get("ticker")
        if key:
            merged_map[key] = p

    merged = list(merged_map.values())

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    logger.info("profiles_saved", total=len(merged), new=len(new_profiles), path=str(OUTPUT_PATH))
    print(f"Saved {len(merged)} profiles ({len(new_profiles)} new)")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
