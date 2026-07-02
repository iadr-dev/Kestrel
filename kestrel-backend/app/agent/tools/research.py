"""Deep Research tool — multi-step analysis combining web search + internal data.

When invoked, performs iterative research:
1. Plans research angles (technical, fundamental, news, macro)
2. Executes multiple searches in parallel (Brave API or DDG fallback)
3. Synthesizes findings into a comprehensive report with sources
"""

import os
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.agent.tools.base import BaseTool, ToolResult

BRAVE_BASE = "https://api.search.brave.com/res/v1"


class DeepResearchTool(BaseTool):
    name = "deep_research"
    description = (
        "Perform deep multi-angle research on a stock or market topic. "
        "Searches multiple sources (web news, analyst opinions, market data) and synthesizes a comprehensive report. "
        "Use for complex questions like '全面分析台積電', 'NVDA investment thesis', or '半導體產業前景'. "
        "Takes longer but provides thorough analysis with citations."
    )
    display_name_template = "深度研究「{topic}」"
    parameters = {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Research topic (e.g. '台積電2026展望', 'AI半導體供應鏈分析', 'NVDA vs AMD comparison')"},
            "angles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Research angles to cover (default: news, analyst, technical, fundamental). Options: news, analyst, technical, fundamental, macro, competitor, risk",
            },
        },
        "required": ["topic"],
    }

    async def execute(self, args: dict[str, Any]) -> ToolResult:
        topic = args["topic"]
        angles = args.get("angles", ["news", "analyst", "fundamental", "risk"])

        # Generate search queries for each angle
        queries = self._generate_queries(topic, angles)

        # Execute all searches in parallel
        import asyncio
        search_tasks = [self._search(q) for q in queries]
        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Compile findings
        findings: list[str] = []
        sources: list[dict[str, str]] = []
        for angle, query, result in zip(angles, queries, results, strict=False):
            if isinstance(result, BaseException):
                findings.append(f"[{angle}] Search failed: {str(result)[:50]}")
                continue
            if not result:
                findings.append(f"[{angle}] No results found for: {query}")
                continue

            section_results = []
            for r in result[:3]:
                section_results.append(f"  • {r['title']}: {r['snippet']}")
                sources.append(r)
            findings.append(f"[{angle.upper()}] Query: \"{query}\"\n" + "\n".join(section_results))

        report = f"Deep Research: {topic}\n{'='*50}\n\n"
        report += "\n\n".join(findings)
        report += f"\n\n---\nSources ({len(sources)} references found across {len(angles)} angles)"

        return ToolResult(
            content=report,
            data={"topic": topic, "angles": angles, "source_count": len(sources), "sources": sources[:10]},
        )

    def _generate_queries(self, topic: str, angles: list[str]) -> list[str]:
        """Generate targeted search queries for each research angle."""
        query_templates: dict[str, str] = {
            "news": f"{topic} 最新消息 新聞 2026",
            "analyst": f"{topic} 分析師 目標價 評等",
            "technical": f"{topic} 技術分析 均線 支撐 壓力",
            "fundamental": f"{topic} 營收 EPS 毛利率 財報",
            "macro": f"{topic} 總經 影響 升息 通膨",
            "competitor": f"{topic} 競爭對手 比較 市佔率",
            "risk": f"{topic} 風險 挑戰 利空 downside",
        }
        return [query_templates.get(a, f"{topic} {a}") for a in angles]

    async def _search(self, query: str) -> list[dict[str, str]]:
        """Search using Brave API (preferred) or DuckDuckGo fallback."""
        brave_key = os.getenv("BRAVE_SEARCH_API_KEY")
        if brave_key:
            return await self._brave_search(query, brave_key)
        return await self._ddg_search(query)

    async def _brave_search(self, query: str, api_key: str) -> list[dict[str, str]]:
        """Brave News + Web search for research."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{BRAVE_BASE}/news/search",
                params={"q": query, "count": 5, "search_lang": "zh-hant", "freshness": "pm"},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = [
                    {"title": r.get("title", ""), "snippet": r.get("description", ""), "url": r.get("url", "")}
                    for r in data.get("results", [])[:5]
                ]
                if results:
                    return results

            # Fallback to web search
            resp = await client.get(
                f"{BRAVE_BASE}/web/search",
                params={"q": query, "count": 5, "search_lang": "zh-hant"},
                headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            )
            if resp.status_code == 200:
                data = resp.json()
                return [
                    {"title": r.get("title", ""), "snippet": r.get("description", ""), "url": r.get("url", "")}
                    for r in data.get("web", {}).get("results", [])[:5]
                ]
        return []

    async def _ddg_search(self, query: str) -> list[dict[str, str]]:
        """Fallback: DuckDuckGo HTML search."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get("https://html.duckduckgo.com/html/", params={"q": query, "kl": "tw-tzh"}, headers=headers)
            if resp.status_code != 200:
                return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict[str, str]] = []
        for item in soup.select(".result")[:5]:
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
