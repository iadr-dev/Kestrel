"""RSS feed scraper — fetch and parse RSS/Atom feeds for financial news."""

import time
from datetime import datetime
from typing import Any

import defusedxml.ElementTree as ET  # type: ignore[import-untyped]  # XXE/billion-laughs safe (feeds are external)
import httpx

from app.core.logging import get_logger
from app.scrapers import ScrapeResult

log = get_logger(__name__)

HEADERS = {
    "User-Agent": "Kestrel/1.0 (Stock Analysis Platform)",
    "Accept": "application/rss+xml, application/xml, text/xml",
}

# Live TW financial + tech RSS feeds. Unlike FinMind's ~1-day-lagged news dataset,
# these publish in near-real-time, so they supply the feed's fresh leading edge.
# Only feeds verified to return well-formed RSS with a plain UA are included
# (ctee = Cloudflare 403, ltn = malformed XML — both deliberately excluded).
DEFAULT_FEEDS: dict[str, str] = {
    # Financial (near-real-time)
    "cnyes_tw": "https://news.cnyes.com/rss/v1/news/category/tw_stock",       # 鉅亨網 台股
    "cnyes_headline": "https://news.cnyes.com/rss/v1/news/category/headline",  # 鉅亨網 頭條
    "udn_money": "https://money.udn.com/rssfeed/news/1001/5590?ch=money",      # 經濟日報
    # Tech / crypto
    "technews": "https://technews.tw/feed/",
    "technews_finance": "https://finance.technews.tw/feed/",
    "ithome": "https://www.ithome.com.tw/rss",
    "blocktempo": "https://www.blocktempo.com/feed/",
}


async def fetch_feed(url: str, max_items: int = 20) -> list[dict[str, Any]]:
    """Fetch and parse a single RSS/Atom feed URL."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            log.warning("rss_fetch_failed", url=url, status=resp.status_code)
            return []

    try:
        # Parse the raw bytes (not resp.text) so the XML declaration's own encoding
        # is honoured — avoids mojibake / parse errors on CJK feeds.
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        log.warning("rss_parse_failed", url=url)
        return []

    items: list[dict[str, Any]] = []

    channel = root.find("channel")
    if channel is not None:
        feed_title = channel.findtext("title", "")
        for item in channel.findall("item")[:max_items]:
            items.append({
                "title": item.findtext("title", "").strip(),
                "link": item.findtext("link", "").strip(),
                "date": _parse_date(item.findtext("pubDate", "")),
                "source": feed_title,
                "description": _clean_html(item.findtext("description", ""))[:200],
            })
        return items

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns)[:max_items]:
        link_el = entry.find("atom:link", ns)
        items.append({
            "title": (entry.findtext("atom:title", namespaces=ns) or "").strip(),
            "link": link_el.get("href", "") if link_el is not None else "",
            "date": _parse_date(entry.findtext("atom:published", namespaces=ns) or entry.findtext("atom:updated", namespaces=ns) or ""),
            "source": root.findtext("atom:title", namespaces=ns) or "",
            "description": _clean_html(entry.findtext("atom:summary", namespaces=ns) or "")[:200],
        })

    if not items:
        for entry in root.findall("entry")[:max_items]:
            link_el = entry.find("link")
            items.append({
                "title": (entry.findtext("title") or "").strip(),
                "link": link_el.get("href", "") if link_el is not None else (entry.findtext("link") or ""),
                "date": _parse_date(entry.findtext("published") or entry.findtext("updated") or ""),
                "source": root.findtext("title") or "",
                "description": _clean_html(entry.findtext("summary") or "")[:200],
            })

    return items


async def fetch_multiple_feeds(feed_urls: dict[str, str] | None = None, max_per_feed: int = 10) -> list[dict[str, Any]]:
    """Fetch multiple RSS feeds and merge results sorted by date."""
    feeds = feed_urls or DEFAULT_FEEDS
    all_items: list[dict[str, Any]] = []

    for name, url in feeds.items():
        try:
            items = await fetch_feed(url, max_per_feed)
            all_items.extend(items)
        except Exception as e:
            log.warning("rss_feed_error", feed=name, error=str(e)[:50])

    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return all_items


def _parse_date(date_str: str) -> str:
    """Parse various date formats to ISO string."""
    if not date_str:
        return ""
    date_str = date_str.strip()

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return date_str[:16]


def _clean_html(html: str) -> str:
    """Strip HTML tags from description."""
    import re
    if not html:
        return ""
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def run(feeds: dict[str, str] | None = None) -> ScrapeResult:
    start = time.perf_counter()
    errors: list[str] = []
    try:
        items = await fetch_multiple_feeds(feeds)
        total_rows = len(items)
    except Exception as e:
        errors.append(str(e))
        total_rows = 0

    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("rss_scrape_done", rows=total_rows, duration_ms=duration_ms)
    return ScrapeResult(source="rss", rows_written=total_rows, duration_ms=duration_ms, errors=errors)
