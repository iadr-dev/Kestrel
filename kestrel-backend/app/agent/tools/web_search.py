"""Web Search & LLM Context tools — powered by Brave Search API.

- web_search: Quick search returning titles/snippets/URLs (Brave Web Search or DDG fallback)
- fetch_page: Deep content extraction from a URL (Brave LLM Context or basic scraping fallback)

Brave API docs: https://api-dashboard.search.brave.com/documentation
"""

import os
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.agent.tools.base import BaseTool, ToolResult

BRAVE_BASE = "https://api.search.brave.com/res/v1"


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the internet for real-time information about stocks, companies, market news, analyst opinions, or any topic not available in local data. Returns search results with titles, snippets, and URLs."
    display_name_template = "搜尋「{query}」"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query (e.g. '台積電 法說會 2026', 'TSMC earnings forecast')"},
            "num_results": {"type": "integer", "description": "Number of results (default 5, max 10)", "default": 5},
            "news_only": {"type": "boolean", "description": "Search news only (better for breaking news, earnings)", "default": False},
        },
        "required": ["query"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        query = args["query"]
        num = min(args.get("num_results", 5), 10)
        news_only = args.get("news_only", False)

        brave_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if brave_key:
            if news_only:
                results = await self._brave_news(query, num, brave_key)
            else:
                results = await self._brave_web(query, num, brave_key)
        else:
            results = await self._search_ddg(query, num)

        if not results:
            return ToolResult(content=f"No search results found for: {query}", error="No results")

        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"[{i}] {r['title']}\n    {r['snippet']}\n    URL: {r['url']}")

        content = f"Search results for \"{query}\" ({len(results)} results):\n\n" + "\n\n".join(formatted)
        return ToolResult(content=content, data={"results": results})

    async def _brave_web(self, query: str, num: int, api_key: str) -> list[dict[str, str]]:
        """Brave Web Search API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BRAVE_BASE}/web/search",
                params={"q": query, "count": num, "search_lang": "zh-hant", "text_decorations": "false"},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [
                {"title": r.get("title", ""), "snippet": r.get("description", ""), "url": r.get("url", "")}
                for r in data.get("web", {}).get("results", [])[:num]
            ]

    async def _brave_news(self, query: str, num: int, api_key: str) -> list[dict[str, str]]:
        """Brave News Search API — better for financial news, time-sensitive queries."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BRAVE_BASE}/news/search",
                params={"q": query, "count": num, "search_lang": "zh-hant", "freshness": "pw"},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("description", ""),
                    "url": r.get("url", ""),
                    "age": r.get("age", ""),
                }
                for r in data.get("results", [])[:num]
            ]

    async def _search_ddg(self, query: str, num: int) -> list[dict[str, str]]:
        """Fallback: DuckDuckGo HTML search (no API key needed)."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get("https://html.duckduckgo.com/html/", params={"q": query, "kl": "tw-tzh"}, headers=headers)
            if resp.status_code != 200:
                return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict[str, str]] = []
        for item in soup.select(".result")[:num]:
            title_el = item.select_one(".result__title a")
            snippet_el = item.select_one(".result__snippet")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            url = href if isinstance(href, str) else ""
            snippet = snippet_el.get_text(strip=True) if snippet_el else ""
            if "uddg=" in url:
                from urllib.parse import parse_qs, unquote, urlparse
                parsed = urlparse(url)
                actual = parse_qs(parsed.query).get("uddg", [""])[0]
                url = unquote(actual)
            if title and url:
                results.append({"title": title, "snippet": snippet, "url": url})
        return results


class FetchPageTool(BaseTool):
    name = "fetch_page"
    description = "Fetch and extract the main text content from a URL. Uses Brave LLM Context API for token-efficient pre-extracted content when available. Use after web_search to read a specific page for more details."
    display_name_template = "讀取網頁內容"
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch content from"},
            "max_tokens": {"type": "integer", "description": "Max tokens to return (default 2000)", "default": 2000},
        },
        "required": ["url"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        url = args["url"]
        max_tokens = args.get("max_tokens", 2000)

        brave_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if brave_key:
            content = await self._brave_llm_context(url, max_tokens, brave_key)
            if content:
                return ToolResult(content=content)

        return await self._basic_fetch(url, max_tokens * 4)

    async def _brave_llm_context(self, url: str, max_tokens: int, api_key: str) -> str | None:
        """Brave LLM Context API — pre-extracted, token-efficient content for LLMs."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{BRAVE_BASE}/llm/context",
                params={
                    "q": url,
                    "maximum_number_of_tokens": max_tokens,
                    "count": 1,
                    "relevance_threshold": "disabled",
                },
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            snippets = []
            for item in data.get("grounding", {}).get("generic", []):
                for snippet in item.get("snippets", []):
                    text = snippet.get("text", "")
                    if text:
                        snippets.append(text)
            if snippets:
                return f"Content from {url}:\n\n" + "\n\n".join(snippets)
            return None

    async def _basic_fetch(self, url: str, max_chars: int) -> ToolResult:
        """Fallback: basic HTML fetch and text extraction."""
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    return ToolResult(content=f"Failed to fetch: HTTP {resp.status_code}", error=f"HTTP {resp.status_code}")

            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            text = "\n".join(lines)[:max_chars]
            return ToolResult(content=f"Content from {url}:\n\n{text}")
        except Exception as e:
            return ToolResult(content=f"Error fetching page: {str(e)[:100]}", error=str(e)[:100])
