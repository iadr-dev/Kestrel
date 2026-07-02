"""Daily market data ingest — fetches ALL market data and stores in DuckDB.

Run after market close (19:00 TW time) via APScheduler or manually.
Usage: python -m scripts.daily_ingest
"""

import asyncio
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd  # type: ignore[import-untyped]

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.constants import FinMindDataset
from app.core.logging import get_logger
from app.db.duckdb.engine import DuckDBEngine, get_duckdb
from app.providers.finmind.provider import FinMindProvider

logger = get_logger(__name__)

_VALID_STOCK_ID = re.compile(r"^[0-9A-Za-z]{1,10}$")

# Rows committed per transaction. A whole-dataset ingest (TaiwanStockPrice alone
# is 20-40k rows incl. warrants) used to run as ONE transaction; DuckDB holds the
# MVCC/undo state for every uncommitted row in memory until COMMIT, so that single
# giant transaction blew past DuckDB's memory_limit and aborted — after which every
# remaining row failed with "Current transaction is aborted". Committing in bounded
# chunks releases that state periodically (and lets readers interleave between
# chunks instead of blocking for the whole ingest).
_CHUNK_SIZE = 5000


def _is_valid_stock_id(stock_id: str | None) -> bool:
    """Validate stock_id format before DuckDB insert."""
    return bool(stock_id and _VALID_STOCK_ID.match(stock_id))


def _chunked_upsert(
    table: str, columns: list[str], rows: list[list[Any]], *, label: str, chunk_size: int = _CHUNK_SIZE
) -> int:
    """Bulk-upsert rows into a DuckDB table in bounded, independently-committed chunks.

    Each chunk is registered as a pandas DataFrame and inserted via a single
    `INSERT OR REPLACE ... SELECT * FROM df` — a true columnar bulk load. This is
    ~400x faster than `executemany`, which loops per-row and does a primary-key
    conflict probe on every row (45k rows: ~0.3s vs >120s). Chunking still bounds
    peak memory for very large datasets and lets readers interleave between commits.

    Cold path: if a chunk's bulk insert fails, its transaction is already rolled
    back by WriteContext.__exit__, so we retry that chunk row-by-row in fresh
    transactions — one bad row drops only itself, never poisoning its neighbours
    or spinning on an aborted transaction.
    """
    if not rows:
        return 0
    db = get_duckdb()
    inserted = 0
    collist = ", ".join(columns)
    for start in range(0, len(rows), chunk_size):
        chunk = rows[start:start + chunk_size]
        try:
            df = pd.DataFrame(chunk, columns=columns)  # noqa: F841 — referenced by name in the SQL below
            with db.write_connection() as conn:
                conn.execute(f"INSERT OR REPLACE INTO {table} ({collist}) SELECT {collist} FROM df")
            inserted += len(chunk)
        except Exception as e:
            logger.warning("ingest_chunk_failed", label=label, size=len(chunk), error=str(e)[:120])
            inserted += _row_by_row_upsert(db, table, columns, chunk, label=label)
    return inserted


def _row_by_row_upsert(db: DuckDBEngine, table: str, columns: list[str], chunk: list[list[Any]], *, label: str) -> int:
    """Per-row fallback for a chunk that failed bulk insert. Each row commits in
    its own transaction so one bad row can't poison the others. Slow but only runs
    on the rare failed chunk."""
    collist = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    sql = f"INSERT OR REPLACE INTO {table} ({collist}) VALUES ({placeholders})"
    inserted = 0
    for params in chunk:
        try:
            with db.write_connection() as conn:
                conn.execute(sql, params)
            inserted += 1
        except Exception as e:
            logger.warning("ingest_row_failed", label=label, error=str(e)[:120])
    return inserted


async def ingest_prices(provider: FinMindProvider, trade_date: date) -> int:
    """Fetch all stock prices for a given date."""
    data = await provider.fetch(
        FinMindDataset.TAIWAN_STOCK_PRICE, start_date=trade_date, end_date=trade_date
    )
    if not data:
        return 0

    rows = [
        [
            row.get("stock_id"),
            row.get("date"),
            row.get("open"),
            row.get("max"),
            row.get("min"),
            row.get("close"),
            row.get("Trading_Volume"),
            row.get("Trading_money"),
            row.get("spread"),
            row.get("Trading_turnover"),
        ]
        for row in data
        if _is_valid_stock_id(row.get("stock_id"))
    ]
    return _chunked_upsert(
        "price_daily",
        ["stock_id", "date", "open", "high", "low", "close", "volume", "amount", "spread", "turnover"],
        rows,
        label="prices",
    )


async def ingest_institutional(provider: FinMindProvider, trade_date: date) -> int:
    """Fetch PER-STOCK institutional buy/sell into institutional_daily.

    Uses TaiwanStockInstitutionalInvestorsBuySell (per-stock), NOT the market-wide
    TaiwanStockTotalInstitutionalInvestors. The per-stock dataset is what the chip
    score consumer queries (ai_scoring.py: WHERE stock_id IN (...)). The market-wide
    total feed is served live by institutional_service.py and does not use this table.
    """
    data = await provider.fetch(
        FinMindDataset.TAIWAN_STOCK_INSTITUTIONAL,
        start_date=trade_date,
        end_date=trade_date,
    )
    if not data:
        return 0

    rows = [
        [
            row.get("stock_id"),
            row.get("date"),
            row.get("name", "unknown"),
            row.get("buy", 0),
            row.get("sell", 0),
        ]
        for row in data
        if _is_valid_stock_id(row.get("stock_id"))
    ]
    return _chunked_upsert(
        "institutional_daily",
        ["stock_id", "date", "institution", "buy", "sell"],
        rows,
        label="institutional",
    )


async def ingest_margin(provider: FinMindProvider, trade_date: date) -> int:
    """Fetch per-stock margin (融資) + short (融券) balances into margin_daily.

    Feeds the chip score's contrarian margin signal (ai_scoring.compute_chip_score).
    """
    data = await provider.fetch(
        FinMindDataset.TAIWAN_STOCK_MARGIN,
        start_date=trade_date,
        end_date=trade_date,
    )
    if not data:
        return 0

    rows = [
        [
            row.get("stock_id"),
            row.get("date"),
            row.get("MarginPurchaseTodayBalance", 0) or 0,
            row.get("ShortSaleTodayBalance", 0) or 0,
        ]
        for row in data
        if _is_valid_stock_id(row.get("stock_id"))
    ]
    return _chunked_upsert(
        "margin_daily",
        ["stock_id", "date", "margin_balance", "short_balance"],
        rows,
        label="margin",
    )


async def ingest_shareholding(provider: FinMindProvider, trade_date: date) -> int:
    """Fetch per-stock 外資持股 (foreign-investor shareholding) into shareholding_daily.

    Feeds the 外資持股率增加/減少 screen. TaiwanStockShareholding returns all stocks
    for `trade_date` (one row per stock) with the foreign-held share count + % of
    issued shares; we store the count, % and issued total.
    """
    data = await provider.fetch(
        FinMindDataset.TAIWAN_STOCK_SHAREHOLDING,
        start_date=trade_date,
        end_date=trade_date,
    )
    if not data:
        return 0

    rows = [
        [
            row.get("stock_id"),
            row.get("date"),
            row.get("ForeignInvestmentShares", 0) or 0,
            row.get("ForeignInvestmentSharesRatio", 0) or 0,
            row.get("NumberOfSharesIssued", 0) or 0,
        ]
        for row in data
        if _is_valid_stock_id(row.get("stock_id"))
    ]
    return _chunked_upsert(
        "shareholding_daily",
        ["stock_id", "date", "foreign_shares", "foreign_ratio", "issued_shares"],
        rows,
        label="shareholding",
    )


def compute_indicators(lookback_days: int = 120) -> int:
    """Precompute KD + MACD per TW stock into indicators_daily (today + prior values
    for cross detection). KD/MACD need the full series + recursive smoothing, so we
    compute them in Python (reusing app.formulas) over each stock's recent closes and
    store only the latest two sessions' values. Reads price_daily directly (no API).
    Returns rows written."""
    import numpy as np

    from app.formulas.oscillators import kd as kd_fn
    from app.formulas.trend import macd as macd_fn

    db = get_duckdb()
    # All 4-digit TW stocks' recent OHLC, oldest→newest, in one scan.
    start = date.today() - timedelta(days=lookback_days)
    rows = db.read_connection().execute(
        """SELECT stock_id, date, close, high, low
           FROM price_daily
           WHERE stock_id SIMILAR TO '[0-9]{4}' AND close > 0 AND date >= ?
           ORDER BY stock_id, date""",
        [start],
    ).fetchall()

    by_stock: dict[str, list[tuple[Any, float, float, float]]] = {}
    for sid, d, c, h, lo in rows:
        by_stock.setdefault(sid, []).append((d, float(c), float(h or c), float(lo or c)))

    out: list[list[Any]] = []
    for sid, series in by_stock.items():
        # Need enough history for MACD (26+9) and KD (9); skip thin names.
        if len(series) < 35:
            continue
        closes = np.array([s[1] for s in series], dtype=np.float64)
        highs = np.array([s[2] for s in series], dtype=np.float64)
        lows = np.array([s[3] for s in series], dtype=np.float64)
        last_date = series[-1][0]

        k = kd_fn(closes, highs, lows)
        m = macd_fn(closes)

        def _val(arr: "np.ndarray[Any, Any]", i: int) -> float | None:
            if 0 <= i < len(arr):
                v = arr[i]
                return None if (v is None or np.isnan(v)) else float(v)
            return None

        out.append([
            sid, last_date,
            _val(k["k"], len(closes) - 1), _val(k["d"], len(closes) - 1),
            _val(k["k"], len(closes) - 2), _val(k["d"], len(closes) - 2),
            _val(m["histogram"], len(closes) - 1), _val(m["histogram"], len(closes) - 2),
        ])

    return _chunked_upsert(
        "indicators_daily",
        ["stock_id", "date", "kd_k", "kd_d", "kd_k_prev", "kd_d_prev", "macd_hist", "macd_hist_prev"],
        out,
        label="indicators",
    )


async def ingest_revenue(provider: FinMindProvider, trade_date: date, months: int = 15) -> int:
    """Fetch monthly revenue for all stocks and store revenue + COMPUTED YoY / MoM.

    Two FinMind quirks force a per-month loop + local computation:
      1. TaiwanStockMonthRevenue (no data_id) returns ONLY the start_date month, so a
         single far-back start_date yields nothing — we loop the last `months` month
         boundaries instead (≈15 calls; trivial on Sponsor 6000/hr) to build history.
      2. The raw rows carry NO growth-rate field — only raw `revenue` + the reporting
         `revenue_year`/`revenue_month`. So YoY (same month, year−1) and MoM (prior
         calendar month) are computed here. The old code stored 0 for both, which
         silently flat-lined the AI fundamental score's revenue dimension.
    """
    # Anchor on the FIRST of trade_date's month, walk back `months` months.
    anchor = trade_date.replace(day=1)

    def _months_back(d: date, n: int) -> date:
        y, m = d.year, d.month - n
        while m <= 0:
            m += 12
            y -= 1
        return date(y, m, 1)

    # Accumulate raw monthly revenue per stock, keyed by (year, month) reporting period.
    # rev[sid][(ry, rm)] = (date_str, revenue)
    rev: dict[str, dict[tuple[int, int], tuple[str, float]]] = {}
    for i in range(months):
        d = _months_back(anchor, i)
        batch = await provider.fetch(FinMindDataset.TAIWAN_STOCK_MONTH_REVENUE, start_date=d)
        for row in batch:
            sid = row.get("stock_id")
            if not _is_valid_stock_id(sid):
                continue
            ry, rm = row.get("revenue_year"), row.get("revenue_month")
            if ry is None or rm is None:
                continue
            rev.setdefault(str(sid), {})[(int(ry), int(rm))] = (str(row.get("date")), float(row.get("revenue") or 0))

    rows: list[list[Any]] = []
    for sid, periods in rev.items():
        for (ry, rm), (d_str, revenue) in periods.items():
            prior_year = periods.get((ry - 1, rm))      # same month, last year → YoY
            prev_month = periods.get((ry, rm - 1)) if rm > 1 else periods.get((ry - 1, 12))  # MoM
            yoy = ((revenue - prior_year[1]) / prior_year[1] * 100) if prior_year and prior_year[1] else 0.0
            mom = ((revenue - prev_month[1]) / prev_month[1] * 100) if prev_month and prev_month[1] else 0.0
            rows.append([sid, d_str, int(revenue), round(yoy, 2), round(mom, 2)])

    return _chunked_upsert(
        "revenue_monthly",
        ["stock_id", "date", "revenue", "revenue_yoy", "revenue_mom"],
        rows,
        label="revenue",
    )


def _recent_quarter_ends(trade_date: date, n: int = 6) -> list[date]:
    """The last `n` quarter-END dates on/before trade_date (FinMind dates statements on
    the period end: 03-31, 06-30, 09-30, 12-31)."""
    q_ends = [(3, 31), (6, 30), (9, 30), (12, 31)]
    out: list[date] = []
    y = trade_date.year
    # Start from the most recent quarter end not after trade_date, walk back.
    candidates = [date(yy, m, d) for yy in range(y, y - (n // 4 + 2), -1) for (m, d) in reversed(q_ends)]
    for qd in sorted(candidates, reverse=True):
        if qd <= trade_date:
            out.append(qd)
        if len(out) >= n:
            break
    return out


async def ingest_financials(provider: FinMindProvider, trade_date: date, quarters: int = 9) -> int:
    """Fetch quarterly financial statements (EPS + margins) into financials_quarterly.

    FinMind TaiwanStockFinancialStatements (no data_id) returns ONLY the start_date
    quarter, so a single far-back start_date yields nothing — we loop the last
    `quarters` quarter-end dates instead. Long-format (one row per type/value); we
    pivot EPS + gross/operating/net margin per stock+quarter, and join the balance
    sheet (same quarter) to derive ROE / ROA / 負債比 / 速動比.
    """
    # Pivot income-statement long rows → {(stock_id, date): {type: value}}.
    pivoted: dict[tuple[str, str], dict[str, float]] = {}
    # Balance-sheet pivot, same shape, for the ratio derivations.
    bs_pivot: dict[tuple[str, str], dict[str, float]] = {}
    for qd in _recent_quarter_ends(trade_date, quarters):
        data = await provider.fetch(FinMindDataset.TAIWAN_STOCK_FINANCIAL_STATEMENTS, start_date=qd)
        for row in data:
            sid = row.get("stock_id")
            d = row.get("date")
            if not _is_valid_stock_id(sid) or not d:
                continue
            pivoted.setdefault((str(sid), str(d)), {})[row.get("type", "")] = row.get("value", 0) or 0

        bs_data = await provider.fetch(FinMindDataset.TAIWAN_STOCK_BALANCE_SHEET, start_date=qd)
        for row in bs_data:
            sid = row.get("stock_id")
            d = row.get("date")
            t = row.get("type", "")
            # Skip the `_per` percentage variants — we only need the raw amounts.
            if not _is_valid_stock_id(sid) or not d or t.endswith("_per"):
                continue
            bs_pivot.setdefault((str(sid), str(d)), {})[t] = row.get("value", 0) or 0

    rows: list[list[Any]] = []
    for (sid, d), vals in pivoted.items():
        revenue = vals.get("Revenue", 0) or 0
        gross = vals.get("GrossProfit", 0) or 0
        op_income = vals.get("OperatingIncome", 0) or 0
        net_income = vals.get("IncomeAfterTaxes", vals.get("EquityAttributableToOwnersOfParent", 0)) or 0
        # Margins as % of revenue (guard divide-by-zero).
        gm = (gross / revenue * 100) if revenue else 0.0
        om = (op_income / revenue * 100) if revenue else 0.0
        nm = (net_income / revenue * 100) if revenue else 0.0

        # Balance-sheet ratios (same stock+quarter). ROE/ROA use the quarter's net
        # income (a single-quarter return, not annualized — consistent across stocks).
        bs = bs_pivot.get((sid, d), {})
        equity = bs.get("Equity", 0) or 0
        total_assets = bs.get("TotalAssets", 0) or 0
        liabilities = bs.get("Liabilities", 0) or 0
        cur_assets = bs.get("CurrentAssets", 0) or 0
        cur_liab = bs.get("CurrentLiabilities", 0) or 0
        inventories = bs.get("Inventories", 0) or 0
        roe = (net_income / equity * 100) if equity else 0.0
        roa = (net_income / total_assets * 100) if total_assets else 0.0
        debt_ratio = (liabilities / total_assets * 100) if total_assets else 0.0
        quick_ratio = ((cur_assets - inventories) / cur_liab * 100) if cur_liab else 0.0

        rows.append([sid, d, vals.get("EPS", 0) or 0, gm, om, nm,
                     round(roe, 2), round(roa, 2), round(debt_ratio, 2), round(quick_ratio, 2),
                     net_income, equity, total_assets])

    return _chunked_upsert(
        "financials_quarterly",
        ["stock_id", "date", "eps", "gross_margin", "operating_margin", "net_margin",
         "roe", "roa", "debt_ratio", "quick_ratio", "net_income", "equity", "total_assets"],
        rows,
        label="financials",
    )


async def ingest_per(provider: FinMindProvider, trade_date: date) -> int:
    """殖利率 / PER / PBR — all stocks for the latest trading day. Source: TaiwanStockPER
    (carries dividend_yield, PER, PBR per stock per day). Feeds 現金殖利率>5% + value screens."""
    data = await provider.fetch(FinMindDataset.TAIWAN_STOCK_PER, start_date=trade_date, end_date=trade_date)
    if not data:
        return 0
    rows = [
        [row.get("stock_id"), row.get("date"),
         row.get("dividend_yield", 0) or 0, row.get("PER", 0) or 0, row.get("PBR", 0) or 0]
        for row in data if _is_valid_stock_id(row.get("stock_id"))
    ]
    return _chunked_upsert("per_daily", ["stock_id", "date", "dividend_yield", "per", "pbr"], rows, label="per")


async def ingest_etf_nav(trade_date: date) -> int:
    """Persist today's ETF NAV / market price / 折溢價 snapshot into etf_nav_daily so the
    detail page has a premium-discount HISTORY (the MIS NAV feed itself is point-in-time).

    Source: TWSE MIS all_etf.txt via app.scrapers.twse_etf (NOT FinMind). One row per
    (etf_id, date); re-running the same day overwrites. Numeric fields arrive as strings
    and are coerced here."""
    from app.scrapers.twse_etf import scrape_etf_nav

    def _num(v: Any) -> float | None:
        try:
            return float(str(v).replace(",", ""))
        except (TypeError, ValueError):
            return None

    try:
        nav_data = await scrape_etf_nav(trade_date)
    except Exception as e:
        logger.warning("etf_nav_scrape_failed", error=str(e)[:120])
        return 0
    if not nav_data:
        return 0

    rows = [
        [
            row.get("etf_id"),
            trade_date,
            _num(row.get("market_price")),
            _num(row.get("estimated_nav")),
            _num(row.get("premium_discount_pct")),
        ]
        for row in nav_data
        if _is_valid_stock_id(row.get("etf_id"))
    ]
    return _chunked_upsert(
        "etf_nav_daily",
        ["etf_id", "date", "market_price", "nav", "premium_discount_pct"],
        rows,
        label="etf_nav",
    )


async def ingest_active_etf_holdings(trade_date: date) -> int:
    """Snapshot every 主動式ETF's FULL holdings into etf_holdings_daily so the 操作日報
    (加碼/減碼/新增/刪除) can diff day-over-day. Source: MoneyDJ (the only feed with the
    complete constituent list). Best-effort per ETF; runs the ~30 ETFs with a small
    concurrency cap to be gentle on the source."""
    from app.scrapers.moneydj_etf import scrape_moneydj_holdings
    from app.scrapers.twse_etf import scrape_etf_fund_info

    try:
        info = await scrape_etf_fund_info()
    except Exception as e:
        logger.warning("active_etf_fund_info_failed", error=str(e)[:120])
        return 0
    active = [
        code for code, prof in (info or {}).items()
        if code.endswith("A") or (prof.get("short_name") or prof.get("name") or "").startswith("主動")
    ]
    if not active:
        return 0

    sem = asyncio.Semaphore(6)

    async def fetch(etf_id: str) -> list[list[Any]]:
        async with sem:
            try:
                holdings = await scrape_moneydj_holdings(etf_id)
            except Exception:
                return []
        return [
            [etf_id, trade_date, h["name"], h.get("shares_lots"), h.get("weight_pct")]
            for h in holdings
            if h.get("name")
        ]

    batches = await asyncio.gather(*[fetch(e) for e in active])
    rows = [r for batch in batches for r in batch]
    return _chunked_upsert(
        "etf_holdings_daily",
        ["etf_id", "date", "stock_name", "shares_lots", "weight_pct"],
        rows,
        label="etf_holdings",
    )


async def ingest_news(trade_date: date | None = None) -> int:
    """Merge FinMind news (day-lagged, but complete) + live RSS feeds (real-time
    leading edge) into news_daily, deduped by link. Runs frequently (news cron) so
    the API serves a current feed without re-scraping per request.

    FinMind gives the last 2 days (for cross-day completeness); RSS gives the fresh
    top-of-feed. Newest-first ordering is by the full `ts` timestamp string."""
    from app.scrapers.rss import fetch_multiple_feeds

    today = trade_date or date.today()
    rows: dict[str, list[Any]] = {}  # link → row (dedupe)

    # 1. FinMind (last 2 days). Timestamps 'YYYY-MM-DD HH:MM:SS'.
    try:
        provider = FinMindProvider(Settings())
        for off in (0, 1):
            d = today - timedelta(days=off)
            data = await provider.fetch(FinMindDataset.TAIWAN_STOCK_NEWS, start_date=d) or []
            for r in data:
                link = (r.get("link") or r.get("url") or "").strip()
                title = (r.get("title") or "").strip()
                if not link or not title:
                    continue
                rows[link] = [
                    link, str(r.get("date") or ""), title,
                    (r.get("source") or "").strip() or None,
                    r.get("stock_id") or None, None, "finmind",
                ]
    except Exception as e:
        logger.warning("news_finmind_failed", error=str(e)[:120])

    # 2. Live RSS (fresh leading edge). RSS date is 'YYYY-MM-DD HH:MM'.
    try:
        for item in await fetch_multiple_feeds():
            link = (item.get("link") or "").strip()
            title = (item.get("title") or "").strip()
            if not link or not title or link in rows:
                continue
            rows[link] = [
                link, (item.get("date") or "").strip(), title,
                (item.get("source") or "").strip() or None,
                None, None, "rss",
            ]
    except Exception as e:
        logger.warning("news_rss_failed", error=str(e)[:120])

    return _chunked_upsert(
        "news_daily",
        ["link", "ts", "title", "source", "stock_id", "thumbnail", "origin"],
        list(rows.values()),
        label="news",
    )


async def _resolve_available_date(provider: FinMindProvider, start: date, lookback: int = 8) -> date:
    """Find the latest date at/just-before `start` that actually has published TWSE
    price data. Today's session may not be published yet (queried before ~15:00, or a
    holiday) — probing with a single liquid stock avoids ingesting an empty day and
    leaving the web on stale data. Falls back to `start` if none found."""
    for offset in range(lookback):
        d = start - timedelta(days=offset)
        if d.weekday() >= 5:  # skip weekends cheaply
            continue
        try:
            probe = await provider.fetch(
                FinMindDataset.TAIWAN_STOCK_PRICE, data_id="2330", start_date=d, end_date=d
            )
            if probe:
                return d
        except Exception:
            continue
    return start


async def daily_ingest(target_date: date | None = None) -> dict[str, int]:
    """Main daily ingest pipeline. Fetches all market data for the last AVAILABLE
    trading date (so the web always shows the most recent published session)."""
    settings = Settings()
    provider = FinMindProvider(settings)
    requested = target_date or date.today()
    # Resolve to the latest date that has published data (handles pre-close / holidays).
    today = await _resolve_available_date(provider, requested)
    if today != requested:
        logger.info("daily_ingest_resolved_date", requested=str(requested), available=str(today))

    logger.info("daily_ingest_start", date=str(today))

    # 1. All stock prices
    price_count = await ingest_prices(provider, today)
    logger.info("prices_ingested", count=price_count, date=str(today))

    # 2. Institutional data
    inst_count = await ingest_institutional(provider, today)
    logger.info("institutional_ingested", count=inst_count, date=str(today))

    # 3. Monthly revenue (covers last 13 months for YoY comparison)
    rev_count = await ingest_revenue(provider, today)
    logger.info("revenue_ingested", count=rev_count, date=str(today))

    # 4. Margin / short balances (contrarian chip signal — changes daily)
    margin_count = await ingest_margin(provider, today)
    logger.info("margin_ingested", count=margin_count, date=str(today))

    # 4b. Foreign shareholding % (外資持股) — feeds the 外資持股率增加/減少 screen.
    holding_count = await ingest_shareholding(provider, today)
    logger.info("shareholding_ingested", count=holding_count, date=str(today))

    # 4c. KD / MACD precompute (reads price_daily; runs AFTER prices land) — feeds the
    # 日KD交叉 / MACD柱狀體轉正轉負 screens. Off the event loop (CPU-bound numpy).
    indicator_count = await asyncio.to_thread(compute_indicators)
    logger.info("indicators_computed", count=indicator_count, date=str(today))

    # 4d. Valuation (殖利率/PER/PBR) — feeds 現金殖利率>5% + PER/PBR value screens.
    per_count = await ingest_per(provider, today)
    logger.info("per_ingested", count=per_count, date=str(today))

    # 4e. ETF NAV / 折溢價 snapshot — builds the premium-discount history for the ETF
    # detail page (TWSE MIS feed, not FinMind). Best-effort: never fails the run.
    etf_nav_count = await ingest_etf_nav(today)
    logger.info("etf_nav_ingested", count=etf_nav_count, date=str(today))

    # 4f. Active-ETF full holdings snapshot (MoneyDJ) — feeds the 操作日報 day-over-day
    # diff (加碼/減碼). Accumulates history; the log is meaningful after ≥2 sessions.
    etf_hold_count = await ingest_active_etf_holdings(today)
    logger.info("etf_holdings_ingested", count=etf_hold_count, date=str(today))

    # Note: quarterly financials (EPS/margins) are NOT ingested here — they only
    # change ~4×/year, so ingest_financials runs on a separate WEEKLY cron
    # (see app/main.py weekly_financials job) to avoid re-fetching identical data
    # 90 days in a row.

    # 5. Fear & Greed (macro)
    fg_data = await provider.fetch(FinMindDataset.CNN_FEAR_GREED_INDEX, start_date=today - timedelta(days=7))
    logger.info("fear_greed_fetched", count=len(fg_data or []))

    logger.info("daily_ingest_complete", prices=price_count, institutional=inst_count, revenue=rev_count, margin=margin_count, shareholding=holding_count, date=str(today))
    return {"prices": price_count, "institutional": inst_count, "revenue": rev_count, "margin": margin_count, "shareholding": holding_count}


# --- Granular per-source jobs --------------------------------------------------
#
# Each TWSE/TPEX dataset is published at a different time after close, so each gets
# its own scheduled job (see app/main.py) timed to its source's release — rather
# than one combined run that has to wait for the LATEST source (margin ~21:00) and
# leaves prices/三大法人 stale for hours. Every job builds its own provider so it's
# self-contained for the scheduler. daily_ingest() above stays as the dev-boot
# one-shot (and any manual full run).

async def ingest_prices_job(target_date: date | None = None) -> int:
    """收盤價 — finalized shortly after the 13:30 close (~15:00)."""
    provider = FinMindProvider(Settings())
    today = await _resolve_available_date(provider, target_date or date.today())
    n = await ingest_prices(provider, today)
    logger.info("prices_ingested", count=n, date=str(today))
    return n


async def ingest_institutional_job(target_date: date | None = None) -> int:
    """三大法人買賣超 (T86) — TWSE ~15:00, TPEX ~16:00."""
    provider = FinMindProvider(Settings())
    today = await _resolve_available_date(provider, target_date or date.today())
    n = await ingest_institutional(provider, today)
    logger.info("institutional_ingested", count=n, date=str(today))
    return n


async def ingest_margin_job(target_date: date | None = None) -> int:
    """融資融券餘額 — TWSE 信用交易統計, published ~21:00 (later than the others)."""
    provider = FinMindProvider(Settings())
    today = await _resolve_available_date(provider, target_date or date.today())
    n = await ingest_margin(provider, today)
    logger.info("margin_ingested", count=n, date=str(today))
    return n


async def ingest_revenue_job(target_date: date | None = None) -> int:
    """月營收 — companies file by the 10th of each month; cheap daily refresh keeps
    the rolling 13-month window current without waiting for a monthly cron."""
    provider = FinMindProvider(Settings())
    today = target_date or date.today()
    n = await ingest_revenue(provider, today)
    logger.info("revenue_ingested", count=n, date=str(today))
    return n


async def ingest_shareholding_job(target_date: date | None = None) -> int:
    """外資持股 (TaiwanStockShareholding) — feeds the 外資持股率增減 screen. Published
    alongside the EOD datasets."""
    provider = FinMindProvider(Settings())
    today = await _resolve_available_date(provider, target_date or date.today())
    n = await ingest_shareholding(provider, today)
    logger.info("shareholding_ingested", count=n, date=str(today))
    return n


async def ingest_per_job(target_date: date | None = None) -> int:
    """殖利率 / PER / PBR (TaiwanStockPER) — feeds value screens + the fundamental
    score's valuation factor."""
    provider = FinMindProvider(Settings())
    today = await _resolve_available_date(provider, target_date or date.today())
    n = await ingest_per(provider, today)
    logger.info("per_ingested", count=n, date=str(today))
    return n


async def compute_indicators_job() -> int:
    """KD / MACD precompute — reads price_daily (no API), so it must run AFTER the
    price job lands. Off the event loop (CPU-bound numpy). Feeds 日KD / MACD screens."""
    n = await asyncio.to_thread(compute_indicators)
    logger.info("indicators_computed", count=n)
    return n


async def ingest_etf_nav_job(target_date: date | None = None) -> int:
    """ETF NAV / 折溢價 snapshot (TWSE MIS) — builds the premium-discount history."""
    today = target_date or date.today()
    n = await ingest_etf_nav(today)
    logger.info("etf_nav_ingested", count=n, date=str(today))
    return n


async def ingest_active_etf_holdings_job(target_date: date | None = None) -> int:
    """Active-ETF full holdings snapshot (MoneyDJ) — accumulates etf_holdings_daily so
    the 操作日報 (加碼/減碼) day-over-day diff has history."""
    today = target_date or date.today()
    n = await ingest_active_etf_holdings(today)
    logger.info("etf_holdings_ingested", count=n, date=str(today))
    return n


async def ingest_news_job(target_date: date | None = None) -> int:
    """News refresh — FinMind (day-lagged) + live RSS merged into news_daily. Runs on
    a short interval so the feed's leading edge tracks the live RSS sources."""
    n = await ingest_news(target_date)
    logger.info("news_ingested", count=n)
    return n


async def weekly_financials(target_date: date | None = None) -> dict[str, int]:
    """Ingest quarterly financial statements (EPS/margins). Runs weekly — the data
    only updates on quarterly report releases, so daily fetching is wasteful."""
    settings = Settings()
    provider = FinMindProvider(settings)
    today = target_date or date.today()
    logger.info("weekly_financials_start", date=str(today))
    fin_count = await ingest_financials(provider, today)
    logger.info("financials_ingested", count=fin_count, date=str(today))
    return {"financials": fin_count}


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    result = asyncio.run(daily_ingest())
    print(f"Ingest complete: {result}")
