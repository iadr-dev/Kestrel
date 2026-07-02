from datetime import date
from typing import Any, cast

from app.core.constants import FinMindDataset
from app.providers.cache import build_cache_key
from app.services.data.base_service import BaseDataService


class InstitutionalService(BaseDataService):
    provider_capability = "institutional"
    default_ttl = 900

    async def get_buy_sell(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "buy_sell", stock_id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_total_buy_sell(
        self, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "total_buy_sell", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_TOTAL_INSTITUTIONAL, start_date=start_date, end_date=end_date)

    async def get_foreign_holding(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "foreign", stock_id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_SHAREHOLDING, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_holding_shares_per(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "holding_per", stock_id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_HOLDING_SHARES_PER, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_holding_distribution(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> dict[str, Any]:
        """Aggregate TDCC 集保 holding-level data into a UI-ready shareholding
        distribution: per-level rows for the latest week, retail/mid/whale buckets,
        the 千張大戶 (>1000-lot) headline %, total holder count, and a weekly trend
        of the whale % so the UI can show whether ownership is concentrating.

        Raw FinMind rows are `{HoldingSharesLevel, people, percent, unit}` per level
        per weekly date — the previous UI read non-existent `percent_under_50` keys,
        so every bar showed 0%."""
        rows = await self.get_holding_shares_per(stock_id, start_date, end_date)
        if not rows:
            return {"stock_id": stock_id, "levels": [], "buckets": {}, "trend": [], "latest_date": None, "total_holders": 0, "whale_pct": None}

        # Group rows by date; ignore the 'total' and adjustment pseudo-levels.
        by_date: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            level = str(r.get("HoldingSharesLevel") or r.get("holding_shares_level") or "")
            if not level or level == "total" or "差異" in level:
                continue
            by_date.setdefault(str(r.get("date")), []).append({
                "level": level,
                "people": int(r.get("people") or 0),
                "percent": float(r.get("percent") or 0.0),
                "shares": int(r.get("unit") or 0),
            })
        if not by_date:
            return {"stock_id": stock_id, "levels": [], "buckets": {}, "trend": [], "latest_date": None, "total_holders": 0, "whale_pct": None}

        # Lot thresholds (1 lot = 1,000 shares): retail <50 lots, mid 50–400, whale >400.
        # 千張大戶 = the ">1,000,000 shares" level (>1000 lots).
        def _max_shares(level: str) -> int:
            """Upper bound (in shares) of a level like '40,001-50,000'; whale levels → huge."""
            digits = level.replace(",", "")
            if "more than" in digits or "以上" in digits:
                return 10**12
            parts = [int(p) for p in digits.replace("-", " ").split() if p.isdigit()]
            return parts[-1] if parts else 0

        def _bucket(level: str) -> str:
            hi = _max_shares(level)
            if hi <= 50_000:
                return "retail"
            if hi <= 400_000:
                return "mid"
            return "whale"

        trend: list[dict[str, Any]] = []
        for d in sorted(by_date):
            day = by_date[d]
            buckets = {"retail": 0.0, "mid": 0.0, "whale": 0.0}
            for lv in day:
                buckets[_bucket(lv["level"])] += lv["percent"]
            whale_1000 = next((lv["percent"] for lv in day if _max_shares(lv["level"]) >= 10**12), 0.0)
            trend.append({"date": d, **{k: round(v, 2) for k, v in buckets.items()}, "whale_1000": round(whale_1000, 2)})

        latest_date = max(by_date)
        latest = sorted(by_date[latest_date], key=lambda lv: _max_shares(lv["level"]))
        latest_buckets = {"retail": 0.0, "mid": 0.0, "whale": 0.0}
        for lv in latest:
            latest_buckets[_bucket(lv["level"])] += lv["percent"]

        return {
            "stock_id": stock_id,
            "latest_date": latest_date,
            "levels": latest,
            "buckets": {k: round(v, 2) for k, v in latest_buckets.items()},
            "whale_pct": next((round(lv["percent"], 2) for lv in latest if _max_shares(lv["level"]) >= 10**12), None),
            "total_holders": sum(lv["people"] for lv in latest),
            "trend": trend,
        }

    async def get_margin(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "margin", stock_id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_MARGIN, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_total_margin(
        self, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "total_margin", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_TOTAL_MARGIN, start_date=start_date, end_date=end_date)

    async def get_margin_maintenance(
        self, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "margin_maint", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_TOTAL_MARGIN_MAINTENANCE, start_date=start_date, end_date=end_date)

    async def get_securities_lending(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "lending", stock_id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_SECURITIES_LENDING, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_short_sale_balances(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "short_sale", stock_id=stock_id, start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_DAILY_SHORT_SALE_BALANCES, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_trading_daily_report(
        self,
        *,
        stock_id: str | None = None,
        securities_trader_id: str | None = None,
        report_date: date | None = None,
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "daily_report", stock_id=stock_id or "", trader=securities_trader_id or "", date=str(report_date))
        cached = await self._cache.get(key)
        if cached:
            return cast(list[dict[str, Any]], cached)
        provider = self._registry.get_primary("institutional")
        kwargs: dict[str, Any] = {}
        if securities_trader_id:
            kwargs["securities_trader_id"] = securities_trader_id
        data = await provider.fetch_dataset(
            FinMindDataset.TAIWAN_STOCK_TRADING_DAILY_REPORT,
            data_id=stock_id,
            start_date=report_date,
            **kwargs,
        )
        await self._cache.set(key, data, ttl=900)
        return data

    # Number of top net-buying / net-selling brokers treated as "main force" (主力)
    # when aggregating broker-level data into the daily 買賣超 / concentration view.
    _MAIN_FORCE_BROKERS = 15

    async def get_trading_report_agg(
        self, stock_id: str, start_date: date, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        """Daily main-force (主力) buy/sell + concentration for a stock.

        FinMind's pre-aggregated dataset (TaiwanStockTradingDailyReportSecIdAgg)
        was discontinued and now always returns 0 rows, so we derive the same
        shape from the per-broker daily report (which works on Sponsor tier):
        for each trading day in the range we sum the top net-buying and
        net-selling brokers into a daily net, count buyers/sellers, and compute
        5-/20-day rolling concentration (main-force net ÷ gross broker turnover).
        """
        import asyncio
        from datetime import timedelta

        key = build_cache_key("inst", "report_agg", stock_id=stock_id, start=str(start_date), end=str(end_date))
        cached = await self._cache.get(key)
        if cached:
            return cast(list[dict[str, Any]], cached)

        end = end_date or date.today()
        # Trading days only (skip weekends); the per-broker report is single-day.
        days = [
            d for d in (start_date + timedelta(days=i) for i in range((end - start_date).days + 1))
            if d.weekday() < 5
        ]
        reports = await asyncio.gather(
            *[self.get_trading_daily_report(stock_id=stock_id, report_date=d) for d in days],
            return_exceptions=True,
        )

        daily: list[dict[str, Any]] = []
        for d, rep in zip(days, reports, strict=False):
            if isinstance(rep, BaseException) or not rep:
                continue
            agg = self._aggregate_broker_day(str(d), rep)
            if agg:
                daily.append(agg)

        daily.sort(key=lambda x: x["date"])
        self._add_rolling_concentration(daily)

        await self._cache.set(key, daily, ttl=900)
        return daily

    def _aggregate_broker_day(self, day: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Collapse one day of per-broker buy/sell into a main-force aggregate."""
        nets: list[float] = []
        total_buy = 0.0
        total_sell = 0.0
        buyers = 0
        sellers = 0
        for r in rows:
            buy = float(r.get("buy") or 0)
            sell = float(r.get("sell") or 0)
            total_buy += buy
            total_sell += sell
            net = buy - sell
            nets.append(net)
            if net > 0:
                buyers += 1
            elif net < 0:
                sellers += 1
        if not nets:
            return None
        nets.sort()
        top_sellers = sum(n for n in nets[: self._MAIN_FORCE_BROKERS] if n < 0)
        top_buyers = sum(n for n in nets[-self._MAIN_FORCE_BROKERS :] if n > 0)
        main_net = top_buyers + top_sellers  # 主力買賣超 (張)
        return {
            "date": day,
            "total_buy": total_buy,
            "total_sell": total_sell,
            "net": main_net,
            "broker_count_buy": buyers,
            "broker_count_sell": sellers,
            # gross broker turnover for the day — denominator for concentration
            "_turnover": total_buy + total_sell,
        }

    def _add_rolling_concentration(self, daily: list[dict[str, Any]]) -> None:
        """Attach 5-/20-day rolling concentration % (main-force net ÷ turnover)."""
        for i, row in enumerate(daily):
            for window, field in ((5, "concentration_5d"), (20, "concentration_20d")):
                lo = max(0, i - window + 1)
                net_sum = sum(r["net"] for r in daily[lo : i + 1])
                turnover = sum(r["_turnover"] for r in daily[lo : i + 1])
                row[field] = round((net_sum / turnover) * 100, 2) if turnover else 0.0
        # Strip the internal turnover field only after every window has been read.
        for row in daily:
            row.pop("_turnover", None)

    async def get_government_bank(
        self, start_date: date
    ) -> list[dict[str, Any]]:
        """Raw government-bank (官股券商) buy/sell rows for a single trading day.

        The FinMind dataset is keyed on a single date (start_date) and returns one
        row per (stock, bank). Most days before the feed publishes are empty, so we
        walk back up to 8 days to the last day with data.
        """
        from datetime import timedelta

        for offset in range(8):
            d = start_date - timedelta(days=offset)
            if d.weekday() >= 5:
                continue
            key = build_cache_key("inst", "gov_bank", start=str(d))
            data = await self._cached_fetch(
                key, FinMindDataset.TAIWAN_GOVERNMENT_BANK_BUY_SELL, start_date=d
            )
            if data:
                return data
        return []

    async def get_government_bank_ranking(
        self, start_date: date, limit: int = 30
    ) -> dict[str, Any]:
        """Per-stock net government-bank buy/sell ranking for the last available day.

        Aggregates the raw (stock, bank) rows into one row per stock: summed buy /
        sell amounts and shares, net amount, and the set of participating banks.
        Returns {"data": [...sorted by |net|...], "trade_date": d}.
        """
        rows = await self.get_government_bank(start_date)
        if not rows:
            return {"data": [], "trade_date": None}

        trade_date = rows[0].get("date")
        by_stock: dict[str, dict[str, Any]] = {}
        for r in rows:
            sid = r.get("stock_id", "")
            if not sid:
                continue
            agg = by_stock.setdefault(
                sid,
                {"stock_id": sid, "buy_amount": 0.0, "sell_amount": 0.0,
                 "buy": 0.0, "sell": 0.0, "banks": set()},
            )
            agg["buy_amount"] += float(r.get("buy_amount") or 0)
            agg["sell_amount"] += float(r.get("sell_amount") or 0)
            agg["buy"] += float(r.get("buy") or 0)
            agg["sell"] += float(r.get("sell") or 0)
            if r.get("bank_name"):
                agg["banks"].add(r["bank_name"])

        result: list[dict[str, Any]] = []
        for agg in by_stock.values():
            net_amount = agg["buy_amount"] - agg["sell_amount"]
            result.append({
                "stock_id": agg["stock_id"],
                "date": trade_date,
                "buy_amount": agg["buy_amount"],
                "sell_amount": agg["sell_amount"],
                "net_amount": net_amount,
                "buy_shares": agg["buy"],
                "sell_shares": agg["sell"],
                "net_shares": agg["buy"] - agg["sell"],
                "bank_count": len(agg["banks"]),
            })
        result.sort(key=lambda x: abs(x["net_amount"]), reverse=True)
        return {"data": result[:limit], "trade_date": trade_date}

    # Investor-type groups for the 三大法人 buy/sell ranking. FinMind's
    # TaiwanStockInstitutionalInvestorsBuySell `name` column uses these raw codes;
    # we map them to the three conventional TW groupings.
    _INVESTOR_GROUPS: dict[str, set[str]] = {
        "foreign": {"Foreign_Investor", "Foreign_Dealer_Self"},  # 外資
        "trust": {"Investment_Trust"},                            # 投信
        "dealer": {"Dealer_self", "Dealer_Hedging"},              # 自營商
    }

    async def _get_all_institutional(self, start_date: date) -> list[dict[str, Any]]:
        """Raw all-stocks institutional buy/sell rows for a single trading day.

        TaiwanStockInstitutionalInvestorsBuySell with NO data_id returns every
        stock for `start_date` (one row per stock×investor-type). The feed is empty
        before it publishes / on non-trading days, so walk back up to 8 days to the
        last day with data — same pattern as get_government_bank."""
        from datetime import timedelta

        for offset in range(8):
            d = start_date - timedelta(days=offset)
            if d.weekday() >= 5:
                continue
            key = build_cache_key("inst", "all_buy_sell", start=str(d))
            data = await self._cached_fetch(
                key, FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL, start_date=d
            )
            if data:
                return data
        return []

    async def get_institutional_ranking(
        self, start_date: date, investor: str = "all", limit: int = 30
    ) -> dict[str, Any]:
        """Per-stock net buy/sell ranking by investor group for the last available day.

        `investor` ∈ {"all" (三大法人), "foreign" (外資), "trust" (投信), "dealer" (自營商)}.
        Aggregates the raw per-stock×investor-type rows into one row per stock with
        summed buy / sell (shares) and net = buy − sell for the selected group, then
        sorts by net descending so the UI can show 買超 (top, net>0) or 賣超 (bottom,
        net<0) by reading from either end. Returns {"data", "trade_date"}.
        """
        rows = await self._get_all_institutional(start_date)
        if not rows:
            return {"data": [], "trade_date": None}

        wanted: set[str] | None = None
        if investor != "all":
            wanted = self._INVESTOR_GROUPS.get(investor)
            if wanted is None:
                return {"data": [], "trade_date": None}

        trade_date = rows[0].get("date")
        by_stock: dict[str, dict[str, Any]] = {}
        for r in rows:
            if wanted is not None and r.get("name") not in wanted:
                continue
            sid = r.get("stock_id", "")
            if not sid:
                continue
            agg = by_stock.setdefault(sid, {"stock_id": sid, "buy": 0.0, "sell": 0.0})
            agg["buy"] += float(r.get("buy") or 0)
            agg["sell"] += float(r.get("sell") or 0)

        result: list[dict[str, Any]] = []
        for agg in by_stock.values():
            net = agg["buy"] - agg["sell"]
            if net == 0:
                continue
            result.append({
                "stock_id": agg["stock_id"],
                "date": trade_date,
                "buy_shares": agg["buy"],
                "sell_shares": agg["sell"],
                "net_shares": net,
            })
        result.sort(key=lambda x: x["net_shares"], reverse=True)
        # Keep the top `limit` net buyers AND bottom `limit` net sellers so the UI
        # can render either direction without a second request.
        trimmed = result[:limit] + result[-limit:] if len(result) > limit * 2 else result
        return {"data": trimmed, "trade_date": trade_date}

    async def get_block_trade(
        self, stock_id: str | None = None, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "block", stock_id=stock_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_BLOCK_TRADE, data_id=stock_id, start_date=start_date, end_date=end_date)

    async def get_disposition(
        self, stock_id: str | None = None, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        key = build_cache_key("inst", "disposition", stock_id=stock_id or "", start=str(start_date), end=str(end_date))
        return await self._cached_fetch(key, FinMindDataset.TAIWAN_STOCK_DISPOSITION, data_id=stock_id, start_date=start_date, end_date=end_date)
