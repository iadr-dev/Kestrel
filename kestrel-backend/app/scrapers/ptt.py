"""PTT scraper — fetch posts from PTT boards (Stock, Beauty, etc.)

Source: https://www.ptt.cc/bbs/{board}/index.html
Requires over18=1 cookie for certain boards.
"""

import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.core.logging import get_logger
from app.providers.http import verify_tls
from app.scrapers import ScrapeResult

log = get_logger(__name__)

PTT_BASE = "https://www.ptt.cc"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html",
    "Accept-Language": "zh-TW,zh;q=0.9",
}
COOKIES = {"over18": "1"}

BOARDS = {
    "stock": "Stock",
    "beauty": "Beauty",
    "gossiping": "Gossiping",
    "tech_job": "Tech_Job",
}


async def scrape_board(board: str, pages: int = 2) -> list[dict[str, Any]]:
    """Scrape recent posts from a PTT board.

    Args:
        board: Board name (e.g., "Stock", "Beauty")
        pages: Number of index pages to fetch (each ~20 posts)

    Returns:
        List of post dicts with: title, author, date, link, push_count, tag
    """
    posts: list[dict[str, Any]] = []

    try:
        client_ctx = httpx.AsyncClient(
            headers=HEADERS,
            cookies=COOKIES,
            follow_redirects=True,
            timeout=15.0,
            verify=verify_tls(),
        )
    except Exception:
        return []

    async with client_ctx as client:
        # Get latest index page to find page number
        index_url = f"{PTT_BASE}/bbs/{board}/index.html"
        try:
            resp = await client.get(index_url)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            log.warning("ptt_connect_failed", board=board)
            return []
        if resp.status_code != 200:
            log.warning("ptt_fetch_failed", board=board, status=resp.status_code)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        posts.extend(_parse_index_page(soup, board))

        # Fetch previous pages
        if pages > 1:
            prev_link = _find_prev_page_link(soup)
            for _ in range(pages - 1):
                if not prev_link:
                    break
                resp = await client.get(f"{PTT_BASE}{prev_link}")
                if resp.status_code != 200:
                    break
                soup = BeautifulSoup(resp.text, "html.parser")
                posts.extend(_parse_index_page(soup, board))
                prev_link = _find_prev_page_link(soup)

    return posts


def _parse_index_page(soup: BeautifulSoup, board: str) -> list[dict[str, Any]]:
    """Parse a single PTT index page into post list."""
    posts = []
    entries = soup.select(".r-ent")

    for entry in entries:
        title_el = entry.select_one(".title a")
        if not title_el:
            continue

        title = title_el.text.strip()
        href = title_el.get("href", "")

        # Author
        author_el = entry.select_one(".meta .author")
        author = author_el.text.strip() if author_el else ""

        # Date
        date_el = entry.select_one(".meta .date")
        date_str = date_el.text.strip() if date_el else ""

        # Push count (popularity)
        push_el = entry.select_one(".nrec span")
        push_count = push_el.text.strip() if push_el else "0"
        if push_count == "爆":
            push_count = "99"
        elif push_count.startswith("X"):
            push_count = "-" + (push_count[1:] or "1")

        # Extract tag [標的] [新聞] [心得] etc.
        tag_match = re.match(r"\[(.+?)\]", title)
        tag = tag_match.group(1) if tag_match else ""

        posts.append({
            "title": title,
            "author": author,
            "date": date_str,
            "link": f"{PTT_BASE}{href}" if href else "",
            "push_count": push_count,
            "tag": tag,
            "board": board,
        })

    return posts


def _find_prev_page_link(soup: BeautifulSoup) -> str | None:
    """Find the '上頁' link from navigation."""
    links = soup.select(".btn-group-paging a")
    for link in links:
        if "上頁" in link.text:
            href = link.get("href")
            return href if isinstance(href, str) else None
    return None


async def scrape_post_content(url: str) -> dict[str, Any] | None:
    """Scrape a single PTT post's full content."""
    async with httpx.AsyncClient(
        headers=HEADERS,
        cookies=COOKIES,
        follow_redirects=True,
        timeout=15.0,
        verify=verify_tls(),
    ) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Main content
        main_content = soup.select_one("#main-content")
        if not main_content:
            return None

        # Extract metalines (author, title, time, board)
        metalines = {}
        for meta in soup.select(".article-metaline"):
            tag = meta.select_one(".article-meta-tag")
            value = meta.select_one(".article-meta-value")
            if tag and value:
                metalines[tag.text.strip()] = value.text.strip()

        # Extract body text (remove metalines and push messages)
        for el in main_content.select(".article-metaline, .article-metaline-right, .push"):
            el.decompose()
        body = main_content.get_text(strip=True)[:2000]

        # Extract push messages (comments)
        pushes = []
        for push in soup.select(".push"):
            push_tag = push.select_one(".push-tag")
            push_userid = push.select_one(".push-userid")
            push_content = push.select_one(".push-content")
            if push_tag and push_content:
                pushes.append({
                    "type": push_tag.text.strip(),
                    "user": push_userid.text.strip() if push_userid else "",
                    "content": push_content.text.strip().lstrip(": "),
                })

        return {
            "title": metalines.get("標題", ""),
            "author": metalines.get("作者", ""),
            "time": metalines.get("時間", ""),
            "board": metalines.get("看板", ""),
            "body": body,
            "pushes": pushes[:20],
            "push_count": len(pushes),
        }


async def run(boards: list[str] | None = None, pages: int = 2) -> ScrapeResult:
    """Run PTT scraper for specified boards."""

    start = time.perf_counter()
    errors: list[str] = []
    total_rows = 0
    target_boards = boards or ["Stock", "Beauty"]

    for board in target_boards:
        try:
            posts = await scrape_board(board, pages)
            total_rows += len(posts)
        except Exception as e:
            errors.append(f"{board}: {e}")

    duration_ms = int((time.perf_counter() - start) * 1000)
    log.info("ptt_scrape_done", rows=total_rows, boards=len(target_boards), duration_ms=duration_ms)
    return ScrapeResult(source="ptt", rows_written=total_rows, duration_ms=duration_ms, errors=errors)
