"""DuckDB connection manager — one connection, concurrent reads, exclusive writes.

DuckDB allows many cursors to read the single process-wide connection in
parallel; only writes need exclusion. Access is therefore guarded by a
readers-writer lock: any number of concurrent readers, or one exclusive writer.
Serializing all reads behind a single mutex (the previous design) bottlenecked
read throughput ~13x under load — fatal at high MAU. The async helpers
(`aquery`/`aexecute`) run the work in a worker thread so DuckDB never blocks the
event loop.
"""

import asyncio
import threading
from types import TracebackType
from typing import Any

import duckdb

from app.core.logging import get_logger

logger = get_logger(__name__)


class _RWLock:
    """Writer-preferring readers-writer lock.

    Multiple readers may hold it simultaneously; a writer holds it exclusively.
    Writer-preferring so a steady stream of reads can't starve a pending write
    (important: the daily ingest/seed must not be indefinitely delayed by
    request traffic). The writer side is reentrant on the owning thread so a
    nested write_connection() can join an outer write transaction.
    """

    def __init__(self) -> None:
        self._cond = threading.Condition(threading.Lock())
        self._readers = 0
        self._writers_waiting = 0
        self._writer: int | None = None  # owning thread id, or None
        self._writer_depth = 0

    def acquire_read(self) -> None:
        me = threading.get_ident()
        with self._cond:
            # A thread that already holds the write lock may read freely.
            if self._writer == me:
                return
            # Wait while a writer holds the lock or writers are queued (writer-pref).
            while self._writer is not None or self._writers_waiting > 0:
                self._cond.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._cond:
            if self._writer == threading.get_ident():
                return
            self._readers -= 1
            if self._readers == 0:
                self._cond.notify_all()

    def acquire_write(self) -> None:
        me = threading.get_ident()
        with self._cond:
            if self._writer == me:  # reentrant
                self._writer_depth += 1
                return
            self._writers_waiting += 1
            try:
                while self._writer is not None or self._readers > 0:
                    self._cond.wait()
            finally:
                self._writers_waiting -= 1
            self._writer = me
            self._writer_depth = 1

    def release_write(self) -> None:
        with self._cond:
            assert self._writer == threading.get_ident()
            self._writer_depth -= 1
            if self._writer_depth == 0:
                self._writer = None
                self._cond.notify_all()


class DuckDBEngine:
    def __init__(
        self,
        db_path: str = "market_data.duckdb",
        read_only: bool = False,
        memory_limit: str | None = None,
        temp_directory: str | None = None,
        max_temp_directory_size: str | None = None,
    ) -> None:
        self._db_path = db_path
        # read_only=True lets multiple processes (API workers/replicas) open the
        # same file concurrently for reads. DuckDB permits unlimited cross-process
        # readers but only ONE read-write opener — so only the writer process
        # (scheduler/ingest) should use read_only=False.
        self._read_only = read_only
        # Memory tuning (see Settings.duckdb_*). memory_limit bounds DuckDB's
        # buffer pool; temp_directory lets it spill to disk instead of OOMing on
        # large transactions/sorts. Default temp_directory to a sibling of the DB
        # file so spill files land on the same volume as the data.
        self._memory_limit = memory_limit
        self._max_temp_directory_size = max_temp_directory_size
        self._temp_directory = temp_directory or (
            None if db_path == ":memory:" else f"{db_path}.tmp"
        )
        # Readers-writer lock: concurrent reads, exclusive (reentrant) writes.
        self._rwlock = _RWLock()
        # Open-transaction nesting depth (see WriteContext). Only the outermost
        # write_connection() issues BEGIN/COMMIT so many per-row upserts batch
        # into ONE commit instead of autocommitting (and fsync'ing) per row.
        self._txn_depth = 0
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def read_only(self) -> bool:
        return self._read_only

    # --- Async, event-loop-safe helpers (preferred in request handlers) ---

    async def aquery(self, sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
        """Run a read query off the event loop and return all rows."""
        return await asyncio.to_thread(self._query_sync, sql, params)

    async def aquery_one(self, sql: str, params: list[Any] | None = None) -> tuple[Any, ...] | None:
        """Run a read query off the event loop and return the first row."""
        return await asyncio.to_thread(self._query_one_sync, sql, params)

    async def aexecute(self, sql: str, params: list[Any] | None = None) -> None:
        """Run a write/DDL statement off the event loop."""
        await asyncio.to_thread(self._execute_sync, sql, params)

    def _query_sync(self, sql: str, params: list[Any] | None) -> list[tuple[Any, ...]]:
        assert self._conn
        self._rwlock.acquire_read()
        try:
            cur = self._conn.cursor()
            return cur.execute(sql, params or []).fetchall()
        finally:
            self._rwlock.release_read()

    def _query_one_sync(self, sql: str, params: list[Any] | None) -> tuple[Any, ...] | None:
        assert self._conn
        self._rwlock.acquire_read()
        try:
            cur = self._conn.cursor()
            return cur.execute(sql, params or []).fetchone()
        finally:
            self._rwlock.release_read()

    def _execute_sync(self, sql: str, params: list[Any] | None) -> None:
        assert self._conn
        self._rwlock.acquire_write()
        try:
            self._conn.execute(sql, params or [])
        finally:
            self._rwlock.release_write()

    def initialize(self) -> None:
        if self._read_only:
            # Read-only openers cannot create tables and the file must already
            # exist (the writer process creates it). DuckDB requires the schema
            # to be present; we just attach.
            self._conn = duckdb.connect(self._db_path, read_only=True)
            self._apply_pragmas()
            logger.info("duckdb_initialized", path=self._db_path, read_only=True)
            return
        self._conn = duckdb.connect(self._db_path)
        self._apply_pragmas()
        self._create_tables()
        logger.info("duckdb_initialized", path=self._db_path, read_only=False)

    def _apply_pragmas(self) -> None:
        """Apply memory/spill tuning. A temp_directory lets DuckDB spill large
        operations to disk instead of failing with an Out-of-Memory Error; a
        memory_limit bounds the buffer pool so it shares RAM politely with the
        rest of the process (uvicorn, the agent runtime, etc.)."""
        assert self._conn
        if self._memory_limit:
            self._conn.execute(f"SET memory_limit='{self._memory_limit}'")
        if self._temp_directory:
            self._conn.execute(f"SET temp_directory='{self._temp_directory}'")
        if self._max_temp_directory_size:
            self._conn.execute(
                f"SET max_temp_directory_size='{self._max_temp_directory_size}'"
            )

    def _create_tables(self) -> None:
        assert self._conn
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS market_cache (
                dataset VARCHAR NOT NULL,
                stock_id VARCHAR,
                date DATE NOT NULL,
                data JSON NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dataset, stock_id, date)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS price_daily (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                amount BIGINT,
                spread DOUBLE,
                turnover DOUBLE,
                PRIMARY KEY (stock_id, date)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS institutional_daily (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                institution VARCHAR NOT NULL,
                buy BIGINT,
                sell BIGINT,
                PRIMARY KEY (stock_id, date, institution)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS revenue_monthly (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                revenue BIGINT,
                revenue_yoy DOUBLE,
                revenue_mom DOUBLE,
                PRIMARY KEY (stock_id, date)
            )
        """)
        # Margin trading (融資融券) — per-stock daily balances. Used as a contrarian
        # signal in the chip score (rising margin = retail leverage building).
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS margin_daily (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                margin_balance BIGINT,
                short_balance BIGINT,
                PRIMARY KEY (stock_id, date)
            )
        """)
        # ETF daily NAV / market price / premium-discount — persisted from the
        # real-time NAV scrape so the 折溢價 (premium/discount) history chart + table
        # have a series (the scrape itself is point-in-time only).
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_nav_daily (
                etf_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                market_price DOUBLE,
                nav DOUBLE,
                premium_discount_pct DOUBLE,
                PRIMARY KEY (etf_id, date)
            )
        """)
        # Market news feed — merged FinMind (day-lagged) + live RSS, deduped by link.
        # Populated by the news ingest cron so the API serves a fast, current feed
        # without re-scraping every request. `ts` is the full publish timestamp used
        # for newest-first ordering; `link` is the natural unique key.
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS news_daily (
                link VARCHAR PRIMARY KEY,
                ts VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                source VARCHAR,
                stock_id VARCHAR,
                thumbnail VARCHAR,
                origin VARCHAR
            )
        """)
        # Active-ETF daily holdings snapshot — one row per (etf_id, date, holding).
        # Persisted nightly from MoneyDJ so we can diff day-over-day into the 操作日報
        # (加碼/減碼/新增/刪除) log; the source only publishes a point-in-time list.
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS etf_holdings_daily (
                etf_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                stock_name VARCHAR NOT NULL,
                shares_lots DOUBLE,
                weight_pct DOUBLE,
                PRIMARY KEY (etf_id, date, stock_name)
            )
        """)
        # Technical indicators (KD / MACD) precomputed per stock per day. KD & MACD
        # need the full price series + recursive smoothing, which is awkward in pure
        # DuckDB SQL — so a precompute job (compute_indicators) derives them from
        # price_daily and stores today's + the prior values needed for cross detection.
        # Feeds the 日KD交叉 / MACD柱狀體轉正轉負 screens.
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS indicators_daily (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                kd_k DOUBLE,
                kd_d DOUBLE,
                kd_k_prev DOUBLE,
                kd_d_prev DOUBLE,
                macd_hist DOUBLE,
                macd_hist_prev DOUBLE,
                PRIMARY KEY (stock_id, date)
            )
        """)
        # Foreign-investor shareholding (外資持股) — per-stock daily foreign-held
        # share count + % of issued shares. Feeds the 外資持股率增加/減少 screen
        # (rank by N-day change in foreign holding %).
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS shareholding_daily (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                foreign_shares BIGINT,
                foreign_ratio DOUBLE,
                issued_shares BIGINT,
                PRIMARY KEY (stock_id, date)
            )
        """)
        # Quarterly financials (EPS / margins) — feeds the fundamental score's
        # profitability dimension (monthly revenue alone misses margins).
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS financials_quarterly (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                eps DOUBLE,
                gross_margin DOUBLE,
                operating_margin DOUBLE,
                net_margin DOUBLE,
                roe DOUBLE,
                roa DOUBLE,
                debt_ratio DOUBLE,
                quick_ratio DOUBLE,
                PRIMARY KEY (stock_id, date)
            )
        """)
        # Balance-sheet-derived ratios + the raw inputs needed for TTM ROE/ROA
        # (single-quarter ROE ≈ 5% is not the 20% annual figure screeners mean, so the
        # screen sums the last 4 quarters' net income over the latest equity/assets).
        # Added later — backfill on pre-existing tables (ADD COLUMN IF NOT EXISTS no-ops
        # when present).
        for _col in ("roe", "roa", "debt_ratio", "quick_ratio", "net_income", "equity", "total_assets"):
            self._conn.execute(f"ALTER TABLE financials_quarterly ADD COLUMN IF NOT EXISTS {_col} DOUBLE")
        # Daily valuation ratios (殖利率 / PER / PBR) — all stocks, one row per day.
        # Source: TaiwanStockPER. Feeds 現金殖利率>5% + PER/PBR value screens.
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS per_daily (
                stock_id VARCHAR NOT NULL,
                date DATE NOT NULL,
                dividend_yield DOUBLE,
                per DOUBLE,
                pbr DOUBLE,
                PRIMARY KEY (stock_id, date)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_metadata (
                dataset VARCHAR NOT NULL,
                stock_id VARCHAR,
                last_date DATE,
                record_count INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (dataset, stock_id)
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                strategy VARCHAR NOT NULL,
                stock_id VARCHAR NOT NULL,
                trigger_date DATE NOT NULL,
                r5 DOUBLE,
                r20 DOUBLE,
                r60 DOUBLE,
                win DOUBLE,
                triggers INTEGER DEFAULT 1,
                PRIMARY KEY (strategy, stock_id, trigger_date)
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS ingest_log (
                job_name VARCHAR NOT NULL,
                run_date DATE NOT NULL,
                record_count INTEGER DEFAULT 0,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (job_name, run_date)
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS figures (
                id VARCHAR PRIMARY KEY,
                name_en VARCHAR NOT NULL,
                name_zh VARCHAR NOT NULL,
                role VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                photo_url VARCHAR,
                associated_stocks JSON DEFAULT '[]'
            )
        """)

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS figure_events (
                id VARCHAR PRIMARY KEY,
                figure_id VARCHAR NOT NULL,
                event_date DATE NOT NULL,
                event_type VARCHAR NOT NULL,
                title VARCHAR NOT NULL,
                description VARCHAR,
                source_url VARCHAR,
                primary_stock_id VARCHAR,
                affected_stocks JSON DEFAULT '[]',
                impact_1d DOUBLE,
                impact_5d DOUBLE,
                impact_30d DOUBLE,
                sentiment VARCHAR,
                importance INTEGER DEFAULT 5
            )
        """)

        # --- Theme / supply-chain reference data (replaces the old data/*.json files) ---
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS themes (
                theme_id VARCHAR PRIMARY KEY,
                name_zh VARCHAR NOT NULL,
                name_en VARCHAR DEFAULT '',
                status VARCHAR DEFAULT 'active',   -- active | proposed | retired
                source VARCHAR DEFAULT 'finmind_industry_chain',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS theme_memberships (
                stock_id VARCHAR NOT NULL,
                theme_id VARCHAR NOT NULL,
                sub_industry VARCHAR DEFAULT '',
                confidence DOUBLE DEFAULT 1.0,
                source VARCHAR DEFAULT 'finmind_industry_chain',
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                removed_at TIMESTAMP,              -- soft delete; NULL = active
                PRIMARY KEY (stock_id, theme_id)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS tier_classification (
                theme_id VARCHAR NOT NULL,
                sub_industry VARCHAR NOT NULL,
                tier VARCHAR NOT NULL,             -- upstream | midstream | downstream
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (theme_id, sub_industry)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS supply_chain_edges (
                from_id VARCHAR NOT NULL,
                to_id VARCHAR NOT NULL,
                type VARCHAR NOT NULL,             -- supplies | customer | competes
                from_name VARCHAR DEFAULT '',
                to_name VARCHAR DEFAULT '',
                confidence VARCHAR DEFAULT 'medium',
                revenue_pct DOUBLE,
                source VARCHAR DEFAULT 'llm_extraction',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                removed_at TIMESTAMP,
                PRIMARY KEY (from_id, to_id, type)
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS theme_change_log (
                id VARCHAR PRIMARY KEY,
                entity VARCHAR NOT NULL,           -- theme | membership | tier | edge
                entity_id VARCHAR NOT NULL,
                action VARCHAR NOT NULL,           -- create | update | retire
                detail VARCHAR DEFAULT '',
                source VARCHAR DEFAULT '',
                ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Performance indexes for common query patterns
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_price_daily_date ON price_daily(date)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_inst_daily_date ON institutional_daily(date)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_revenue_date ON revenue_monthly(date)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_figure_events_date ON figure_events(event_date)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_figure_events_figure ON figure_events(figure_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_membership_theme ON theme_memberships(theme_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_membership_stock ON theme_memberships(stock_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_from ON supply_chain_edges(from_id)")
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_to ON supply_chain_edges(to_id)")

    def read_connection(self) -> duckdb.DuckDBPyConnection:
        """Get a raw cursor for read operations (synchronous).

        Prefer the async `aquery`/`aquery_one` helpers in request handlers — they
        serialize access and run off the event loop. This raw accessor is retained
        for scripts and startup code where blocking is acceptable.
        """
        assert self._conn
        return self._conn.cursor()

    def write_connection(self) -> "WriteContext":
        """Acquire the write lock and return a transaction-scoped context manager.

        The block runs inside a single DuckDB transaction (committed on success,
        rolled back on error). Nested write_connection() calls on the same thread
        join the outer transaction, so a loop of per-row upserts each opening its
        own block still produces ONE commit. This avoids DuckDB's default
        per-statement autocommit, which fsyncs once per row (~12x slower on bulk
        seeds/ingests — see scripts/seed_themes.py)."""
        if self._read_only:
            raise RuntimeError(
                "write_connection() called on a read-only DuckDB engine. Writes "
                "must run in the writer process (scheduler/ingest), not API workers."
            )
        return WriteContext(self)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


    def get_stock_count(self) -> int:
        assert self._conn
        result = self._conn.execute("SELECT COUNT(DISTINCT stock_id) FROM price_daily").fetchone()
        return result[0] if result else 0

    def compute_backtest_ma_cross(self) -> list[dict[str, Any]]:
        """MA golden cross backtest from DuckDB price_daily."""
        assert self._conn
        sql = """
        WITH ma AS (
            SELECT stock_id, date, close,
                AVG(close) OVER (PARTITION BY stock_id ORDER BY date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as ma5,
                AVG(close) OVER (PARTITION BY stock_id ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as ma20
            FROM price_daily
        ),
        signals AS (
            SELECT *, LAG(ma5) OVER (PARTITION BY stock_id ORDER BY date) as prev_ma5,
                LAG(ma20) OVER (PARTITION BY stock_id ORDER BY date) as prev_ma20
            FROM ma WHERE ma5 IS NOT NULL AND ma20 IS NOT NULL
        ),
        crosses AS (
            SELECT stock_id, date, close FROM signals
            WHERE ma5 > ma20 AND prev_ma5 <= prev_ma20
        ),
        returns AS (
            SELECT c.stock_id,
                (LEAD(p.close, 5) OVER w - c.close) / c.close * 100 as r5,
                (LEAD(p.close, 20) OVER w - c.close) / c.close * 100 as r20,
                (LEAD(p.close, 60) OVER w - c.close) / c.close * 100 as r60
            FROM crosses c JOIN price_daily p ON c.stock_id = p.stock_id AND c.date = p.date
            WINDOW w AS (PARTITION BY c.stock_id ORDER BY c.date)
        )
        SELECT stock_id as k, ROUND(AVG(r5),1) as r5, ROUND(AVG(r20),1) as r20, ROUND(AVG(r60),1) as r60,
            ROUND(SUM(CASE WHEN r5 > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 0) as win,
            COUNT(*) as triggers
        FROM returns WHERE r5 IS NOT NULL
        GROUP BY stock_id ORDER BY win DESC LIMIT 10
        """
        try:
            rows = self._conn.execute(sql).fetchall()
            cols = ["k", "r5", "r20", "r60", "win", "triggers"]
            return [dict(zip(cols, row, strict=False)) for row in rows]
        except Exception:
            return []

    def compute_backtest_breakout(self) -> list[dict[str, Any]]:
        """20-day breakout backtest from DuckDB price_daily."""
        assert self._conn
        sql = """
        WITH highs AS (
            SELECT stock_id, date, close,
                MAX(close) OVER (PARTITION BY stock_id ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING) as high_20
            FROM price_daily
        ),
        signals AS (
            SELECT stock_id, date, close FROM highs WHERE close > high_20 AND high_20 IS NOT NULL
        ),
        returns AS (
            SELECT s.stock_id,
                (LEAD(p.close, 5) OVER w - s.close) / s.close * 100 as r5,
                (LEAD(p.close, 20) OVER w - s.close) / s.close * 100 as r20,
                (LEAD(p.close, 60) OVER w - s.close) / s.close * 100 as r60
            FROM signals s JOIN price_daily p ON s.stock_id = p.stock_id AND s.date = p.date
            WINDOW w AS (PARTITION BY s.stock_id ORDER BY s.date)
        )
        SELECT stock_id as k, ROUND(AVG(r5),1) as r5, ROUND(AVG(r20),1) as r20, ROUND(AVG(r60),1) as r60,
            ROUND(SUM(CASE WHEN r5 > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 0) as win,
            COUNT(*) as triggers
        FROM returns WHERE r5 IS NOT NULL
        GROUP BY stock_id ORDER BY win DESC LIMIT 10
        """
        try:
            rows = self._conn.execute(sql).fetchall()
            cols = ["k", "r5", "r20", "r60", "win", "triggers"]
            return [dict(zip(cols, row, strict=False)) for row in rows]
        except Exception:
            return []


# Singleton for backward compatibility. Used by scripts/cron (writers) and by
# services that fall back to it. Defaults to read-write so writer processes work;
# API workers get a read-only engine via app.state (see app/main.py), not this.
_instance: DuckDBEngine | None = None


def get_duckdb() -> DuckDBEngine:
    global _instance
    if _instance is None:
        # Honor the configured path so scripts and the app agree on the file.
        from app.core.config import Settings
        settings = Settings()
        _instance = DuckDBEngine(
            db_path=settings.duckdb_path,
            memory_limit=settings.duckdb_memory_limit,
            temp_directory=settings.duckdb_temp_directory,
            max_temp_directory_size=settings.duckdb_max_temp_size,
        )
        _instance.initialize()
    return _instance


def set_duckdb(engine: DuckDBEngine) -> None:
    """Install a pre-built engine as the process singleton (used at app startup
    so get_duckdb() callers share the app's configured engine)."""
    global _instance
    _instance = engine


class WriteContext:
    """Transaction-scoped write context for the shared DuckDB connection.

    Holds the engine's write lock (exclusive against readers and other writers)
    for the duration of the block and wraps it in a single transaction. Only the
    outermost context issues BEGIN/COMMIT (tracked via the engine's `_txn_depth`);
    nested contexts on the same thread reuse that transaction so batched writes
    commit exactly once. On exception the outermost context rolls back the whole
    transaction.
    """

    def __init__(self, engine: "DuckDBEngine") -> None:
        self._engine = engine
        self._conn = engine._conn
        self._rwlock = engine._rwlock
        self._outermost = False

    def __enter__(self) -> duckdb.DuckDBPyConnection:
        self._rwlock.acquire_write()
        assert self._conn
        if self._engine._txn_depth == 0:
            self._conn.execute("BEGIN TRANSACTION")
            self._outermost = True
        self._engine._txn_depth += 1
        return self._conn

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            self._engine._txn_depth -= 1
            if self._outermost:
                assert self._conn
                if exc_type is None:
                    self._conn.execute("COMMIT")
                else:
                    self._conn.execute("ROLLBACK")
        finally:
            self._rwlock.release_write()
