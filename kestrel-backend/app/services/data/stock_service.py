from datetime import date
from typing import Any, cast

from app.core.constants import FinMindDataset
from app.db.duckdb.market_cache import MarketDataCache
from app.formulas import compute_indicators
from app.providers.cache import CacheBackend, build_cache_key
from app.providers.registry import ProviderRegistry


class StockService:
    def __init__(
        self,
        registry: ProviderRegistry,
        cache: CacheBackend,
        market_cache: MarketDataCache | None = None,
    ) -> None:
        self._registry = registry
        self._cache = cache
        self._market_cache = market_cache

    async def get_price(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        # L1: in-memory hot cache
        cache_key = build_cache_key("finmind", "price", stock_id=stock_id, start=str(start_date), end=str(end_date))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)

        # L2: DuckDB columnar store
        if self._market_cache:
            duckdb_data = await self._market_cache.get_price_data(stock_id, start_date, end_date)
            if duckdb_data:
                await self._cache.set(cache_key, duckdb_data, ttl=60)
                return duckdb_data

        # L3: FinMind API
        provider = self._registry.get_primary("stock_price")
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

        # Write-through to DuckDB
        if self._market_cache and data:
            await self._market_cache.store_price_data(data)

        await self._cache.set(cache_key, data, ttl=60)
        return data

    async def get_price_adjusted(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE_ADJ,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_price_with_indicators(
        self,
        stock_id: str,
        start_date: date,
        end_date: date | None = None,
        indicators: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        data = await self.get_price(stock_id, start_date, end_date)
        if not data:
            return {"data": [], "indicators": {}}

        close = [r["close"] for r in data]
        high = [r.get("max", r.get("high", r["close"])) for r in data]
        low = [r.get("min", r.get("low", r["close"])) for r in data]
        volume = [r.get("Trading_Volume", r.get("volume", 0)) for r in data]
        # Real open prices (FinMind 'open') so candlestick patterns aren't phantoms.
        open_ = [r.get("open", r["close"]) for r in data]

        indicator_results = compute_indicators(
            close=close, high=high, low=low, volume=volume, indicators=indicators, open_=open_
        )
        return {"data": data, "indicators": indicator_results}

    async def get_price_tick(self, stock_id: str, trade_date: date) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PRICE_TICK,
            data_id=stock_id,
            start_date=trade_date,
        )

    async def get_kbar(self, stock_id: str, trade_date: date) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_KBAR,
            data_id=stock_id,
            start_date=trade_date,
        )

    async def get_week_price(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_WEEK_PRICE,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_month_price(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_MONTH_PRICE,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_stock_info(self) -> list[dict[str, Any]]:
        cache_key = build_cache_key("finmind", "stock_info")
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("stock_info")
        data = await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_INFO)
        await self._cache.set(cache_key, data, ttl=86400)
        return data

    async def get_per(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_PER,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_snapshot(self, stock_id: str | None = None) -> list[dict[str, Any]]:
        """Real-time TW tick snapshot. Cached ~10s so that many concurrent client
        polls (the live RealtimeTab / marquee / watchlist) collapse into ~1 upstream
        FinMind call per window — keeps us well under the rate limit and shields the
        provider under load. 10s is fresh enough for a research UI."""
        cache_key = build_cache_key("finmind", "snapshot", stock_id=stock_id or "all")
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("real_time")
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_TICK_SNAPSHOT,
            data_id=stock_id,
        )
        await self._cache.set(cache_key, data, ttl=10)
        return data

    async def get_trading_dates(self) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_info")
        return await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_TRADING_DATE)

    async def get_price_limits(
        self, stock_id: str | None = None, start_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Get all stock prices for the latest available trading day on/before
        start_date (used for hot stocks ranking + the chat marquee).

        FinMind's TaiwanStockPrice returns ONLY the `start_date` day's rows, so a
        non-trading start_date (weekend / a week ago) yields nothing — which left
        the marquee showing all "—". Walk back up to 8 days to the first day with
        data so callers always get a populated, current snapshot."""
        from datetime import timedelta

        provider = self._registry.get_primary("stock_price")
        anchor = start_date or date.today()
        for offset in range(8):
            d = anchor - timedelta(days=offset)
            if d.weekday() >= 5:
                continue
            data = await provider.fetch_dataset(
                FinMindDataset.TAIWAN_STOCK_PRICE, data_id=stock_id, start_date=d,
            )
            if data:
                return data
        return []

    async def get_day_trading(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_DAY_TRADING,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_suspended(
        self, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_SUSPENDED,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_10_year(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        provider = self._registry.get_primary("stock_price")
        return await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_10_YEAR,
            data_id=stock_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_market_news(self, start_date: date | None = None) -> list[dict[str, Any]]:
        """Market news, newest-first — served from the news_daily table (FinMind +
        live RSS, merged/deduped by the news cron), so the leading edge tracks the
        real-time RSS sources instead of FinMind's ~1-day lag.

        Falls back to a live FinMind fetch if news_daily is empty (fresh DB before the
        first cron run). Short-cached so bursts don't re-query DuckDB. The `updated_at`
        stamp on each item is the FEED refresh time (set by the caller/endpoint)."""
        from datetime import timedelta

        from app.providers.cache import build_cache_key

        cache_key = build_cache_key("news", "market")
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)

        # Primary path: read the cron-populated table (newest-first by full timestamp).
        try:
            from app.db.duckdb.engine import get_duckdb
            rows = await get_duckdb().aquery(
                "SELECT link, ts, title, source, stock_id, thumbnail FROM news_daily "
                "ORDER BY ts DESC LIMIT 40"
            )
            if rows:
                out = [
                    {"link": r[0], "date": r[1], "title": r[2], "source": r[3],
                     "stock_id": r[4], "thumbnail": r[5]}
                    for r in rows
                ]
                await self._cache.set(cache_key, out, ttl=300)
                return out
        except Exception:
            pass

        # Fallback: live FinMind day-by-day merge (pre-cron / empty table).
        import asyncio
        provider = self._registry.get_primary("news")
        today = date.today()
        start = start_date or (today - timedelta(days=7))
        span = min((today - start).days, 14)
        days = [today - timedelta(days=o) for o in range(span + 1)]

        async def one(d: date) -> list[dict[str, Any]]:
            try:
                return await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_NEWS, start_date=d) or []
            except Exception:
                return []

        batches = await asyncio.gather(*[one(d) for d in days])
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for batch in batches:
            for row in batch:
                key = f"{row.get('title', '')}|{row.get('link') or row.get('url', '')}"
                if key in seen:
                    continue
                seen.add(key)
                merged.append(row)
        merged.sort(key=lambda x: x.get("date", ""), reverse=True)
        return merged[:30]

    async def get_stock_news(self, stock_id: str, start_date: date | None = None) -> list[dict[str, Any]]:
        """Per-stock news as a rolling feed over [start_date, today], newest-first.

        Same FinMind quirk as get_market_news: TaiwanStockNews with a data_id still
        returns ONLY the `start_date` day's rows, so a single call gives one stale
        day (the reported "6-day-old news"). We fetch each day start→today in
        parallel, merge/dedupe/sort by full timestamp, then enrich the newest items
        with an og:image thumbnail."""
        import asyncio
        import re
        from datetime import timedelta

        import httpx

        from app.providers.cache import build_cache_key

        today = date.today()
        start = start_date or (today - timedelta(days=7))
        cache_key = build_cache_key("news", "stock", stock_id=stock_id, start=str(start))
        cached = await self._cache.get(cache_key)
        if cached:
            return cast(list[dict[str, Any]], cached)

        provider = self._registry.get_primary("news")
        span = min((today - start).days, 14)
        days = [today - timedelta(days=o) for o in range(span + 1)]

        async def one(d: date) -> list[dict[str, Any]]:
            try:
                return await provider.fetch_dataset(FinMindDataset.TAIWAN_STOCK_NEWS, data_id=stock_id, start_date=d) or []
            except Exception:
                return []

        batches = await asyncio.gather(*[one(d) for d in days])
        seen: set[str] = set()
        data: list[dict[str, Any]] = []
        for batch in batches:
            for row in batch:
                key = f"{row.get('title', '')}|{row.get('link') or row.get('url', '')}"
                if key in seen:
                    continue
                seen.add(key)
                data.append(row)
        data.sort(key=lambda x: x.get("date", ""), reverse=True)

        top = (data or [])[:30]

        # Scrape og:image thumbnails for the newest items, concurrently (the old
        # sequential loop was slow, so it gave up after a handful and most rows
        # came back image-less). Bounded to the first 16 by a semaphore.
        sem = asyncio.Semaphore(8)

        def _extract_og(html: str) -> str | None:
            for pat in (
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
            ):
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    url = m.group(1).strip()
                    return url if url.startswith("http") else None
            return None

        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=3.0, read=5.0, write=3.0, pool=3.0), follow_redirects=True) as client:
            async def thumb(link: str) -> str | None:
                if not link:
                    return None
                async with sem:
                    try:
                        resp = await client.get(link, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                        if resp.status_code == 200:
                            return _extract_og(resp.text[:20000])
                    except Exception:
                        return None
                return None

            links = [item.get("link", "") for item in top[:16]]
            thumbs = await asyncio.gather(*[thumb(link) for link in links])

        thumb_map = {link: th for link, th in zip(links, thumbs, strict=False) if th}
        enriched = [{**item, "thumbnail": thumb_map.get(item.get("link", ""))} for item in top]

        await self._cache.set(cache_key, enriched, ttl=1800)
        return enriched
