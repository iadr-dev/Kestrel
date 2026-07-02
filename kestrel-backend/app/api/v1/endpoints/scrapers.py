"""Scraper endpoints — only true HTML/RSS scrapers that aren't backed by a provider."""

from typing import Any

from fastapi import APIRouter, Query

from app.schemas.common import DataListResponse, DataResponse

router = APIRouter(prefix="/scrapers", tags=["Scrapers"])


@router.get("/rss", response_model=DataListResponse)
async def get_rss_feeds(feed_url: str | None = Query(None)) -> dict[str, Any]:
    """Get financial news from RSS feeds. Optionally pass a custom feed URL."""
    from urllib.parse import urlparse

    from app.scrapers.rss import fetch_feed, fetch_multiple_feeds
    try:
        if feed_url:
            parsed = urlparse(feed_url)
            if parsed.scheme not in ("http", "https"):
                return {"data": [], "count": 0, "error": "Only http/https URLs allowed"}
            if parsed.hostname and (parsed.hostname.startswith("10.") or parsed.hostname.startswith("192.168.")
                                    or parsed.hostname.startswith("172.") or parsed.hostname in ("localhost", "127.0.0.1", "169.254.169.254")):
                return {"data": [], "count": 0, "error": "Internal URLs not allowed"}
            data = await fetch_feed(feed_url, max_items=20)
        else:
            data = await fetch_multiple_feeds(max_per_feed=10)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/ptt/{board}", response_model=DataListResponse)
async def get_ptt_board(board: str, pages: int = Query(default=2, ge=1, le=5)) -> dict[str, Any]:
    """Get PTT board posts (Stock, Beauty, etc.)."""
    from app.scrapers.ptt import BOARDS, scrape_board
    board_name = BOARDS.get(board.lower(), board)
    try:
        data = await scrape_board(board_name, pages)
        return {"data": data, "count": len(data)}
    except Exception as e:
        return {"data": [], "count": 0, "error": str(e)[:100]}


@router.get("/ptt/{board}/post", response_model=DataResponse)
async def get_ptt_post(board: str, url: str = Query(...)) -> dict[str, Any]:
    """Get a single PTT post's full content."""
    from app.scrapers.ptt import scrape_post_content
    try:
        data = await scrape_post_content(url)
        if data:
            return {"data": data}
        return {"data": None, "error": "Post not found"}
    except Exception as e:
        return {"data": None, "error": str(e)[:100]}
