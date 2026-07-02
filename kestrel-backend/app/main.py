"""Kestrel API — FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import date
from typing import TYPE_CHECKING

from fastapi import FastAPI

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Environment, Settings
from app.core.constants import (
    DAILY_SCORING_TOP_N,
    SUPPLY_CHAIN_EXTRACTION_TOP_N,
    WEEKLY_SUMMARIES_MAX_STOCKS,
)
from app.core.logging import get_logger, setup_logging

logger = get_logger(__name__)
# Import formula modules to trigger registration. importlib is used (instead of
# `import app.formulas.X`) so the module-level name `app` is not bound to the
# package here — that would collide with the `app = create_app()` entrypoint.
import importlib

for _formula_module in (
    "app.formulas.moving_average",
    "app.formulas.oscillators",
    "app.formulas.patterns",
    "app.formulas.trend",
    "app.formulas.volatility",
    "app.formulas.volume",
):
    importlib.import_module(_formula_module)
from app.agent.core import AgentService
from app.agent.router import LLMRouter
from app.agent.tools.analysis import GetIndicatorsTool, GetScoreTool
from app.agent.tools.ask_user import AskUserTool
from app.agent.tools.fundamental import (
    GetCapitalReductionTool,
    GetDividendTool,
    GetFinancialsTool,
    GetMarketValueTool,
)
from app.agent.tools.institutional import (
    GetBlockTradeTool,
    GetGovernmentBankTool,
    GetMainForceTool,
    GetMarginMaintenanceTool,
    GetMarginTool,
    GetSecuritiesLendingTool,
    GetShareholdingTool,
    GetShortSaleBalanceTool,
)
from app.agent.tools.market import (
    GetAdvanceDeclineTool,
    GetDayTradingTool,
    GetForeignByIndustryTool,
    GetFuturesAfterHoursTool,
    GetInstitutionalFlowTool,
    GetIntlPriceTool,
    GetMacroDataTool,
    GetMarketIndexTool,
    GetRevenueTool,
    GetStockPriceTool,
    ScreenStocksTool,
)
from app.agent.tools.memory_tools import ForgetFactTool, LearnFactTool, RecallContextTool
from app.agent.tools.mops_tools import (
    GetAnnouncementsTool,
    GetDirectorHoldingsTool,
    GetInvestorConferenceTool,
    GetTreasuryStockTool,
)
from app.agent.tools.rankings_tools import (
    GetInstitutionalRankingsTool,
    GetMarginRankingsTool,
    GetStockRankingsTool,
)
from app.agent.tools.registry import ToolRegistry
from app.agent.tools.render import (
    RenderActiveEtfHoldersTool,
    RenderAlertConfirmTool,
    RenderChartTool,
    RenderComparisonTableTool,
    RenderDividendHistoryTool,
    RenderEsgScorecardTool,
    RenderEtfProfileTool,
    RenderFinancialStatementTool,
    RenderInstitutionalFlowTool,
    RenderKlineChartTool,
    RenderOptionsSentimentTool,
    RenderScoreGaugeTool,
    RenderShareholderGiftTool,
    RenderShortPositionTool,
    RenderStockCardTool,
    RenderSupplyChainTool,
    RenderThemeOverviewTool,
)
from app.agent.tools.research import DeepResearchTool
from app.agent.tools.tdcc_tools import (
    GetDirectorCustodyTool,
    GetMonthlyCustodyChangeTool,
    GetShareholdingDistributionTool,
    GetWeeklyBalanceTool,
)
from app.agent.tools.twse_tools import (
    GetActiveEtfHoldersTool,
    GetBacktestResultTool,
    GetCompanyESGTool,
    GetCompanyProfileTool,
    GetDisposalStocksTool,
    GetDividendScheduleTool,
    GetETFDataTool,
    GetFuturesPositionTool,
    GetMarketHolidaysTool,
    GetNoticeStocksTool,
    GetOddLotTool,
    GetOptionsAnalyticsTool,
    GetOTCStockTool,
    GetPutCallRatioTool,
    GetRealtimeQuoteTool,
    GetShareholderGiftTool,
    GetSupplyChainTool,
    GetThemeStocksTool,
    GetTWSEInstitutionalTool,
    GetWarrantInfoTool,
)
from app.agent.tools.user_tools import ScheduleAlertTool, SetPreferenceTool
from app.agent.tools.web_search import FetchPageTool, WebSearchTool
from app.agent.tools.yfinance_tools import (
    GetAnalystTargetTool,
    GetEarningsCalendarTool,
    GetHoldersTool,
    GetMarketScreenerTool,
    GetMarketSearchTool,
    GetNewsTool,
    GetPeersTool,
    GetSectorInfoTool,
    GetStockHistoryTool,
)
from app.agent.tools.yfinance_tools import (
    GetFinancialsTool as GetYFFinancialsTool,
)
from app.db.duckdb import DuckDBEngine, MarketDataCache
from app.db.session import close_engine, create_engine_and_session, create_tables
from app.middleware.cors import setup_cors
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.providers.base import ProviderCapability
from app.providers.cache import create_cache
from app.providers.finmind import FinMindProvider
from app.providers.registry import ProviderRegistry
from app.services.platform.auth_service import AuthService


async def _ensure_admin_users(
    session_factory: "async_sessionmaker[AsyncSession]",
) -> None:
    """Seed admin/pro users and ensure LINE admin is pro."""
    from sqlalchemy import select

    from app.dependencies import get_settings
    from app.models.user import OAuthAccount, User

    settings = get_settings()

    async with session_factory() as session:
        # Ensure email-based admins are pro
        for email in settings.admin_emails:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                if existing.tier != "pro":
                    existing.tier = "pro"
            else:
                session.add(User(email=email, display_name="Ray", tier="pro"))

        # Ensure LINE admin is pro
        stmt = select(User).join(OAuthAccount).where(
            OAuthAccount.provider == "line",
            OAuthAccount.provider_user_id == settings.admin_line_id,
        )
        result = await session.execute(stmt)
        line_user = result.scalar_one_or_none()
        if line_user and line_user.tier != "pro":
            line_user.tier = "pro"

        await session.commit()


def _seed_figures_if_empty(duckdb_engine: "DuckDBEngine") -> None:
    """Auto-seed figures table if empty — dev convenience + first-run init."""
    try:
        cursor = duckdb_engine.read_connection()
        count = cursor.execute("SELECT COUNT(*) FROM figures").fetchone()
        if count and count[0] > 0:
            return
        import json
        from uuid import uuid4

        from scripts.seed_figures import FIGURES, SAMPLE_EVENTS
        with duckdb_engine.write_connection() as conn:
            for fig in FIGURES:
                conn.execute(
                    "INSERT INTO figures VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [fig["id"], fig["name_en"], fig["name_zh"], fig["role"], fig["category"], fig["photo_url"], json.dumps(fig["associated_stocks"])],
                )
            for evt in SAMPLE_EVENTS:
                conn.execute(
                    "INSERT INTO figure_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [str(uuid4()), evt["figure_id"], evt["event_date"], evt["event_type"], evt["title"], evt["description"], None, evt["primary_stock_id"], json.dumps(evt["affected_stocks"]), evt["impact_1d"], evt["impact_5d"], evt["impact_30d"], evt["sentiment"], evt["importance"]],
                )
        logger.info("figures_seeded", figures=len(FIGURES), events=len(SAMPLE_EVENTS))
    except Exception as e:
        logger.warning("figures_seed_skipped", error=str(e)[:100])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = Settings()
    setup_logging(debug=settings.debug)

    # In production the rate limiter and cache MUST be shared across workers, so
    # Redis is required — fail fast rather than silently degrading to per-process
    # in-memory state (which would let users bypass rate limits ×N workers).
    if settings.environment == Environment.PRODUCTION and not settings.effective_redis_url:
        raise RuntimeError(
            "Redis (UPSTASH_REDIS_REST_URL/_TOKEN) is required when ENVIRONMENT=production: "
            "rate limiting and caching must be shared across workers."
        )

    # Cache: Redis-first with in-memory fallback (see create_cache). Both backends
    # expose start_pruning — a no-op on Redis (native TTL), active prune loop on InMemory.
    cache = create_cache(redis_url=settings.effective_redis_url)
    cache.start_pruning(interval=300)

    # Providers
    finmind = FinMindProvider(settings)
    await finmind.initialize()

    registry = ProviderRegistry()
    registry.register(
        finmind,
        capabilities=[
            ProviderCapability.STOCK_PRICE,
            ProviderCapability.STOCK_INFO,
            ProviderCapability.INSTITUTIONAL,
            ProviderCapability.FUNDAMENTAL,
            ProviderCapability.DERIVATIVE,
            ProviderCapability.REAL_TIME,
            ProviderCapability.INTERNATIONAL,
            ProviderCapability.MACRO,
            ProviderCapability.CONVERTIBLE_BOND,
            ProviderCapability.NEWS,
        ],
    )

    # DuckDB (columnar market data cache). Path + read_only come from Settings so
    # API workers can open read-only (many concurrent readers across processes)
    # while the writer process (scheduler/ingest) opens read-write.
    from app.db.duckdb.engine import set_duckdb
    duckdb_engine = DuckDBEngine(
        db_path=settings.duckdb_path,
        read_only=settings.duckdb_read_only,
        memory_limit=settings.duckdb_memory_limit,
        temp_directory=settings.duckdb_temp_directory,
        max_temp_directory_size=settings.duckdb_max_temp_size,
    )
    duckdb_engine.initialize()
    # Share this engine with get_duckdb() callers (services/scripts) in-process.
    set_duckdb(duckdb_engine)
    market_cache = MarketDataCache(duckdb_engine)

    # Auto-seed figures if table is empty (dev convenience). Skipped on read-only
    # engines — only the writer process seeds.
    if not duckdb_engine.read_only:
        _seed_figures_if_empty(duckdb_engine)

    # Dev mode: run all data jobs once on startup so the UI has data immediately.
    # Production uses scheduled cron jobs instead.
    import asyncio

    def _get_last_trading_date() -> date:
        """Mirror frontend useTradingDate logic — returns last TW market trading date."""
        from datetime import datetime, timezone
        from datetime import timedelta as td
        tw_tz = timezone(td(hours=8))
        now_tw = datetime.now(tw_tz)
        target = now_tw.date()
        day = target.weekday()  # Mon=0 ... Sun=6

        if day == 6:  # Sunday → Friday
            target -= td(days=2)
        elif day == 5:  # Saturday → Friday
            target -= td(days=1)
        elif now_tw.hour < 14:  # Before market close (13:30 + buffer)
            if day == 0:  # Monday before close → last Friday
                target -= td(days=3)
            else:
                target -= td(days=1)
        return target

    async def _dev_boot_all_jobs() -> None:
        """Run all data pipeline jobs once in sequence (dev convenience)."""
        trade_date = _get_last_trading_date()

        # Ingest when the table is empty OR stale (latest stored date is behind the
        # last trading day). Previously this only fired when the table was empty, so
        # a dev server that was offline across trading days never caught up — leaving
        # /price-limits stuck on an old date while per-stock /price (live FinMind) was
        # current. Comparing MAX(date) to the last trading day fixes that.
        try:
            cursor = duckdb_engine.read_connection()
            # Use the latest COMPLETE session (≥500 rows), not MAX(date) — an aborted
            # intraday ingest can leave a 2-row partial day as MAX(date), which would
            # otherwise look "current" and suppress the re-ingest that fills it in.
            row = cursor.execute(
                "SELECT MAX(date) FROM (SELECT date, COUNT(*) n FROM price_daily GROUP BY date) "
                "WHERE n >= 500"
            ).fetchone()
            latest = row[0] if row else None
            if latest is None:
                needs_ingest = True
            else:
                latest_str = str(latest)[:10]
                needs_ingest = latest_str < str(trade_date)
                if needs_ingest:
                    logger.info("dev_boot_ingest_stale", latest_complete=latest_str, last_trading=str(trade_date))
        except Exception:
            needs_ingest = True

        # History-depth check: the multi-day screens (trend = MA5/20/60, ma_reclaim_*,
        # strong_Nd, bollinger, breakout) and the institutional streak screens need a
        # window of past sessions in DuckDB — a single day's ingest leaves them empty.
        # A fresh dev DB (or one that only ever ran the single-day daily_ingest) would
        # silently return nothing for those screens. When we have fewer than the MA60
        # minimum of complete trading days, backfill a full history window instead of a
        # single day. 60 trading days satisfies MA60; we backfill 120 CALENDAR days
        # (~80 trading days, the backfill_prices default) for a comfortable warm-up
        # margin. FinMind Sponsor (6000 req/hr) makes the ~240 calls trivial. Idempotent
        # (INSERT OR REPLACE), so re-running never duplicates.
        MIN_TRADING_DAYS = 60
        BACKFILL_CALENDAR_DAYS = 120
        try:
            cursor = duckdb_engine.read_connection()
            row = cursor.execute(
                "SELECT COUNT(*) FROM (SELECT date FROM price_daily GROUP BY date HAVING COUNT(*) >= 500)"
            ).fetchone()
            history_days = row[0] if row else 0
        except Exception:
            history_days = 0
        needs_backfill = history_days < MIN_TRADING_DAYS

        try:
            if needs_backfill:
                from datetime import timedelta as _td
                backfill_start = trade_date - _td(days=BACKFILL_CALENDAR_DAYS)
                logger.info(
                    "dev_boot_job_starting", job="backfill_history",
                    have_days=history_days, want_trading_days=MIN_TRADING_DAYS,
                    start=str(backfill_start), end=str(trade_date),
                )
                from scripts.backfill_prices import backfill
                await backfill(backfill_start, trade_date)
                logger.info("dev_boot_job_complete", job="backfill_history")
                # backfill() covers prices/inst/margin/shareholding/indicators but NOT
                # the valuation + ETF datasets — run those once for `trade_date` so a
                # FRESH dev DB has PER/ETF NAV/ETF holdings on the first boot (not only
                # after a second boot flips to the daily_ingest branch below).
                from scripts.daily_ingest import (
                    ingest_active_etf_holdings,
                    ingest_etf_nav,
                    ingest_per_job,
                )
                try:
                    await ingest_per_job(trade_date)
                    await ingest_etf_nav(trade_date)
                    await ingest_active_etf_holdings(trade_date)
                    logger.info("dev_boot_job_complete", job="backfill_etf_per_extras")
                except Exception as e:
                    logger.warning("dev_boot_job_failed", job="backfill_etf_per_extras", error=str(e)[:100])
            elif needs_ingest:
                logger.info("dev_boot_job_starting", job="daily_ingest", trade_date=str(trade_date))
                from scripts.daily_ingest import daily_ingest
                await daily_ingest(target_date=trade_date)
                logger.info("dev_boot_job_complete", job="daily_ingest")

            logger.info("dev_boot_job_starting", job="daily_scoring")
            from scripts.daily_scoring import run_daily_scoring
            await run_daily_scoring(top_n=DAILY_SCORING_TOP_N)
            logger.info("dev_boot_job_complete", job="daily_scoring")

            # AI summaries — generate on dev boot too (previously weekly-cron-only, so a
            # fresh dev DB had scores but blank summaries). Uses the LLM if a key is set.
            logger.info("dev_boot_job_starting", job="ai_summaries")
            from scripts.weekly_ai_summaries import generate_summaries
            await generate_summaries(max_stocks=WEEKLY_SUMMARIES_MAX_STOCKS)
            logger.info("dev_boot_job_complete", job="ai_summaries")
        except Exception as e:
            logger.warning("dev_boot_job_failed", job="ingest/scoring", error=str(e)[:100])

        try:
            # Seed theme/membership/tier data into DuckDB from FinMind (idempotent).
            cursor = duckdb_engine.read_connection()
            theme_count = cursor.execute("SELECT COUNT(*) FROM themes").fetchone()
            if not theme_count or theme_count[0] == 0:
                logger.info("dev_boot_job_starting", job="seed_themes")
                from scripts.seed_themes import seed_all
                await seed_all()
                logger.info("dev_boot_job_complete", job="seed_themes")
                # Discover emerging themes from news/events (only if an LLM key is set).
                if settings.gemini_api_key:
                    from app.services.platform.theme_discovery import discover_themes
                    await discover_themes()
                    logger.info("dev_boot_job_complete", job="theme_discovery")
        except Exception as e:
            logger.warning("dev_boot_job_failed", job="seed_themes", error=str(e)[:100])

        try:
            logger.info("dev_boot_job_starting", job="scrape_profiles")
            from scripts.scrape_profiles import scrape_tw_profiles, scrape_us_profiles
            await scrape_tw_profiles()
            await scrape_us_profiles()
            logger.info("dev_boot_job_complete", job="scrape_profiles")
        except Exception as e:
            logger.warning("dev_boot_job_failed", job="scrape_profiles", error=str(e)[:100])

    if duckdb_engine.read_only:
        # Read-only API worker: never seeds or ingests (the writer process does).
        logger.info("boot_jobs_skipped", reason="duckdb_read_only")
    elif settings.environment == "development":
        asyncio.create_task(_dev_boot_all_jobs())
    else:
        # Production: only ingest/seed if empty
        try:
            cursor = duckdb_engine.read_connection()
            price_count = cursor.execute("SELECT COUNT(*) FROM price_daily").fetchone()
            theme_count = cursor.execute("SELECT COUNT(*) FROM themes").fetchone()
            needs_ingest = not price_count or price_count[0] == 0
            needs_themes = not theme_count or theme_count[0] == 0
            if needs_ingest or needs_themes:
                async def _first_boot_ingest() -> None:
                    try:
                        if needs_ingest:
                            from scripts.daily_ingest import daily_ingest
                            await daily_ingest()
                            # Score immediately so /ai/rankings isn't empty until the
                            # next scheduled run on a fresh deploy.
                            from scripts.daily_scoring import run_daily_scoring
                            await run_daily_scoring(top_n=DAILY_SCORING_TOP_N)
                        if needs_themes:
                            from scripts.seed_themes import seed_all
                            await seed_all()
                    except Exception as e:
                        logger.warning("first_boot_ingest_failed", error=str(e)[:100])
                asyncio.create_task(_first_boot_ingest())
        except Exception as e:
            logger.warning("first_boot_ingest_skipped", error=str(e)[:100])

    # SQLite/Postgres (user data)
    session_factory = create_engine_and_session(settings)
    await create_tables()
    await _ensure_admin_users(session_factory)

    # Agent system
    from app.services.data.derivative_service import DerivativeService
    from app.services.data.fundamental_service import FundamentalService
    from app.services.data.institutional_service import InstitutionalService
    from app.services.data.international_service import InternationalService
    from app.services.data.macro_service import MacroService
    from app.services.data.market_service import MarketService
    from app.services.data.screener_service import ScreenerService
    from app.services.data.stock_service import StockService

    stock_svc = StockService(registry=registry, cache=cache, market_cache=market_cache)
    market_svc = MarketService(registry=registry, cache=cache)
    institutional_svc = InstitutionalService(registry=registry, cache=cache)
    fundamental_svc = FundamentalService(registry=registry, cache=cache)
    macro_svc = MacroService(registry=registry, cache=cache)
    screener_svc = ScreenerService(registry=registry, cache=cache)
    international_svc = InternationalService(registry=registry, cache=cache)
    derivative_svc = DerivativeService(registry=registry, cache=cache)

    tool_registry = ToolRegistry()
    tool_registry.register_many([
        # Market data
        GetStockPriceTool(stock_svc),
        GetMarketIndexTool(market_svc),
        GetInstitutionalFlowTool(institutional_svc),
        GetRevenueTool(fundamental_svc),
        GetMacroDataTool(macro_svc),
        ScreenStocksTool(screener_svc),
        # Institutional / chip
        GetMarginTool(institutional_svc),
        GetShareholdingTool(institutional_svc),
        GetMainForceTool(institutional_svc),
        GetGovernmentBankTool(institutional_svc),
        GetShortSaleBalanceTool(institutional_svc),
        GetSecuritiesLendingTool(institutional_svc),
        GetBlockTradeTool(institutional_svc),
        GetMarginMaintenanceTool(institutional_svc),
        # Fundamental
        GetFinancialsTool(fundamental_svc),
        GetDividendTool(fundamental_svc),
        GetMarketValueTool(fundamental_svc),
        GetCapitalReductionTool(fundamental_svc),
        # Market breadth / sentiment / day-trading / international / futures
        GetAdvanceDeclineTool(market_svc),
        GetForeignByIndustryTool(),
        GetDayTradingTool(stock_svc),
        GetIntlPriceTool(international_svc),
        GetFuturesAfterHoursTool(derivative_svc),
        # Analysis
        GetIndicatorsTool(stock_svc),
        GetScoreTool(stock_svc),
        # User interaction
        AskUserTool(),
        ScheduleAlertTool(),
        SetPreferenceTool(),
        # Memory
        RecallContextTool(),
        LearnFactTool(),
        ForgetFactTool(),
        # Rich output
        RenderStockCardTool(),
        RenderComparisonTableTool(),
        RenderScoreGaugeTool(),
        RenderChartTool(),
        RenderAlertConfirmTool(),
        RenderSupplyChainTool(),
        RenderThemeOverviewTool(),
        RenderKlineChartTool(),
        RenderInstitutionalFlowTool(),
        RenderFinancialStatementTool(),
        RenderDividendHistoryTool(),
        RenderShortPositionTool(),
        RenderOptionsSentimentTool(),
        RenderEsgScorecardTool(),
        RenderEtfProfileTool(),
        RenderActiveEtfHoldersTool(),
        RenderShareholderGiftTool(),
        # Web search & research
        WebSearchTool(),
        FetchPageTool(),
        DeepResearchTool(),
        # yfinance-powered (analyst, calendar, holders)
        GetAnalystTargetTool(),
        GetEarningsCalendarTool(),
        GetHoldersTool(),
        # TWSE direct (realtime, notice stocks, disposition, institutional, futures)
        GetRealtimeQuoteTool(),
        GetNoticeStocksTool(),
        GetDisposalStocksTool(),
        GetTWSEInstitutionalTool(),
        GetFuturesPositionTool(),
        # Extended TWSE tools (company, theme, ETF, OTC, options, backtest, ESG)
        GetCompanyProfileTool(),
        GetSupplyChainTool(),
        GetThemeStocksTool(),
        GetETFDataTool(),
        GetActiveEtfHoldersTool(),
        GetShareholderGiftTool(),
        GetOTCStockTool(),
        GetPutCallRatioTool(),
        GetOptionsAnalyticsTool(),
        GetBacktestResultTool(),
        GetCompanyESGTool(),
        GetWarrantInfoTool(),
        GetMarketHolidaysTool(),
        GetOddLotTool(),
        GetDividendScheduleTool(),
        # yfinance extended (history, financials, search, screener, sector, news, peers)
        GetStockHistoryTool(),
        GetYFFinancialsTool(),
        GetMarketSearchTool(),
        GetMarketScreenerTool(),
        GetSectorInfoTool(),
        GetNewsTool(),
        GetPeersTool(),
        # TDCC (shareholding distribution, director custody, weekly balance, monthly change)
        GetShareholdingDistributionTool(),
        GetDirectorCustodyTool(),
        GetWeeklyBalanceTool(),
        GetMonthlyCustodyChangeTool(),
        # MOPS (announcements, treasury stock, investor conferences, director holdings)
        GetAnnouncementsTool(),
        GetTreasuryStockTool(),
        GetInvestorConferenceTool(),
        GetDirectorHoldingsTool(),
        # Rankings (official TWSE: volume leaders, institutional buy/sell, margin)
        GetStockRankingsTool(),
        GetInstitutionalRankingsTool(),
        GetMarginRankingsTool(),
    ])

    from app.agent.skills.registry import SkillRegistry
    skill_registry = SkillRegistry()

    llm_router = LLMRouter(settings)
    agent_service = AgentService(
        settings=settings,
        router=llm_router,
        tool_registry=tool_registry,
        skill_registry=skill_registry,
    )

    # Channel gateway (LINE + Telegram)
    from app.channels.gateway import ChannelGateway
    from app.channels.line import LineAdapter
    from app.channels.telegram import TelegramAdapter

    channel_gateway = ChannelGateway(agent_service)
    if settings.line_messaging_access_token:
        channel_gateway.register_adapter(LineAdapter(settings))
    if settings.telegram_bot_token:
        channel_gateway.register_adapter(TelegramAdapter(settings))

    # Services stored on app state
    app.state.provider_registry = registry
    app.state.cache = cache
    app.state.market_cache = market_cache
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.auth_service = AuthService(settings, cache=cache)
    app.state.agent_service = agent_service
    app.state.channel_gateway = channel_gateway

    # Scheduler (daily ingest jobs)
    from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
    from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

    scheduler = AsyncIOScheduler()

    # Event-driven cache invalidation: when an ingest job writes fresh data to
    # DuckDB, immediately bust the cached API responses derived from it so the
    # NEXT request repopulates from the new data instead of serving the stale
    # TTL'd copy. We bust by key prefix (build_cache_key joins with ":"), using
    # the app's actual cache instance — in prod that's the shared Redis every
    # API container reads, so all workers see the refreshed data at once.
    async def _bust(*prefixes: str) -> None:
        total = 0
        for p in prefixes:
            try:
                total += await cache.clear_pattern(f"{p}*")
            except Exception as e:
                logger.warning("cache_invalidate_failed", prefix=p, error=str(e)[:120])
        if total:
            logger.info("cache_invalidated", prefixes=list(prefixes), keys=total)

    # Each market dataset is published at a different time after the 13:30 close,
    # so each ingests on its own schedule (timed to its source's release) instead
    # of one combined run gated by the latest source. Keeps every dataset as fresh
    # as the upstream site allows. Each job is independent — one failing doesn't
    # block the others. After a successful run each busts the cache namespaces
    # whose responses derive from the data it just wrote.
    async def _run_ingest_prices() -> None:
        from scripts.daily_ingest import ingest_prices_job
        try:
            await ingest_prices_job()
            # Everything computed from price_daily: raw prices, screener, ETF list,
            # market breadth / advance-decline.
            await _bust("finmind:price", "screener:", "etf:", "market:")
        except Exception as e:
            logger.error("scheduled_ingest_prices_failed", error=str(e)[:200])

    async def _run_ingest_institutional() -> None:
        from scripts.daily_ingest import ingest_institutional_job
        try:
            await ingest_institutional_job()
            await _bust("inst:")
        except Exception as e:
            logger.error("scheduled_ingest_institutional_failed", error=str(e)[:200])

    async def _run_ingest_margin() -> None:
        from scripts.daily_ingest import ingest_margin_job
        try:
            await ingest_margin_job()
            # Margin/short balances live under the institutional namespace.
            await _bust("inst:margin", "inst:total_margin", "inst:short_sale")
        except Exception as e:
            logger.error("scheduled_ingest_margin_failed", error=str(e)[:200])

    async def _run_ingest_revenue() -> None:
        from scripts.daily_ingest import ingest_revenue_job
        try:
            await ingest_revenue_job()
            await _bust("fund:")
        except Exception as e:
            logger.error("scheduled_ingest_revenue_failed", error=str(e)[:200])

    async def _run_ingest_shareholding() -> None:
        from scripts.daily_ingest import ingest_shareholding_job
        try:
            await ingest_shareholding_job()
            # Foreign-holding screens live under the institutional + screener namespaces.
            await _bust("inst:", "screener:")
        except Exception as e:
            logger.error("scheduled_ingest_shareholding_failed", error=str(e)[:200])

    async def _run_ingest_per() -> None:
        from scripts.daily_ingest import ingest_per_job
        try:
            await ingest_per_job()
            # PER/PBR/yield feed value screens + the fundamental score's valuation factor.
            await _bust("fund:", "screener:")
        except Exception as e:
            logger.error("scheduled_ingest_per_failed", error=str(e)[:200])

    async def _run_compute_indicators() -> None:
        # KD/MACD read price_daily, so this must run AFTER prices land. Same 16:30 slot
        # but APScheduler runs jobs concurrently; the price job finishes well within the
        # window, and a stale-by-one-run indicator set self-heals next day.
        from scripts.daily_ingest import compute_indicators_job
        try:
            await compute_indicators_job()
            await _bust("screener:")
        except Exception as e:
            logger.error("scheduled_compute_indicators_failed", error=str(e)[:200])

    async def _run_ingest_etf_nav() -> None:
        from scripts.daily_ingest import ingest_etf_nav_job
        try:
            await ingest_etf_nav_job()
            await _bust("etf:")
        except Exception as e:
            logger.error("scheduled_ingest_etf_nav_failed", error=str(e)[:200])

    async def _run_ingest_etf_holdings() -> None:
        from scripts.daily_ingest import ingest_active_etf_holdings_job
        try:
            await ingest_active_etf_holdings_job()
            await _bust("etf:")
        except Exception as e:
            logger.error("scheduled_ingest_etf_holdings_failed", error=str(e)[:200])

    async def _run_ingest_news() -> None:
        from scripts.daily_ingest import ingest_news_job
        try:
            n = await ingest_news_job()
            await _bust("news:")
            # Notify connected clients (web/mobile/desktop) that the feed advanced.
            if n:
                from app.push import broker, events
                await broker.publish(events.NEWS_UPDATED, {"count": n})
        except Exception as e:
            logger.error("scheduled_ingest_news_failed", error=str(e)[:200])

    async def _run_alert_check() -> None:
        """Check all active alerts and deliver notifications."""
        try:
            from app.services.platform.alert_delivery import AlertDelivery
            from app.services.platform.alert_engine import AlertEngine
            engine = AlertEngine()
            delivery = AlertDelivery(settings)
            async with session_factory() as session:
                triggered = await engine.check_all_alerts(session)
                for alert in triggered:
                    await delivery.deliver(alert, session)
                await session.commit()
                if triggered:
                    logger.info("alerts_triggered_and_delivered", count=len(triggered))
                    from app.push import broker, events
                    await broker.publish(events.ALERT_TRIGGERED, {"count": len(triggered)})
        except Exception as e:
            logger.error("alert_check_failed", error=str(e)[:200])

    async def _run_daily_scoring() -> None:
        """Pre-compute AI scores after fresh data is ingested."""
        try:
            from scripts.daily_scoring import run_daily_scoring
            await run_daily_scoring(top_n=DAILY_SCORING_TOP_N)
            from app.push import broker, events
            await broker.publish(events.SCORES_REFRESHED, {})
        except Exception as e:
            logger.error("daily_scoring_failed", error=str(e)[:200])

    async def _run_weekly_themes() -> None:
        """Refresh themes: re-seed base taxonomy from FinMind, then LLM discovery.

        1. seed_all() upserts the FinMind industry-chain base (catches new
           listings / industry changes) into DuckDB — idempotent.
        2. discover_themes() finds emerging themes from recent news/events and
           writes them as status='proposed'.
        """
        try:
            from scripts.seed_themes import seed_all
            await seed_all()
        except Exception as e:
            logger.error("weekly_theme_seed_failed", error=str(e)[:200])
        try:
            from app.services.platform.theme_discovery import discover_themes
            await discover_themes()
        except Exception as e:
            logger.error("weekly_theme_discovery_failed", error=str(e)[:200])

    async def _run_weekly_summaries() -> None:
        """Generate AI summaries for top stocks (weekly)."""
        try:
            from scripts.weekly_ai_summaries import generate_summaries
            await generate_summaries(max_stocks=WEEKLY_SUMMARIES_MAX_STOCKS)
        except Exception as e:
            logger.error("weekly_summaries_failed", error=str(e)[:200])

    async def _run_weekly_financials() -> None:
        """Ingest quarterly financials (EPS/margins). Weekly — data is quarterly."""
        try:
            from scripts.daily_ingest import weekly_financials
            await weekly_financials()
        except Exception as e:
            logger.error("weekly_financials_failed", error=str(e)[:200])

    # Per-source ingest, each timed to when its TWSE/TPEX source publishes (TW time
    # shown; cron is UTC, TW = UTC+8). Staggered a little past each release to let
    # the upstream site finish writing.
    #   收盤價 (prices)            finalized ~15:00 TW  → 16:30 TW = 08:30 UTC
    #   三大法人 (institutional)    TWSE 15:00 / TPEX 16:00 → 16:30 TW = 08:30 UTC
    #   融資融券 (margin)          信用交易統計 ~21:00 TW → 21:30 TW = 13:30 UTC
    #   月營收 (revenue)           filed by the 10th; cheap daily refresh → 22:00 TW = 14:00 UTC
    scheduler.add_job(_run_ingest_prices, CronTrigger(hour=8, minute=30), id="ingest_prices")
    scheduler.add_job(_run_ingest_institutional, CronTrigger(hour=8, minute=30), id="ingest_institutional")
    scheduler.add_job(_run_ingest_margin, CronTrigger(hour=13, minute=30), id="ingest_margin")
    scheduler.add_job(_run_ingest_revenue, CronTrigger(hour=14, minute=0), id="ingest_revenue")
    # 外資持股 (TaiwanStockShareholding) — same EOD release as prices → 16:30 TW = 08:30 UTC
    scheduler.add_job(_run_ingest_shareholding, CronTrigger(hour=8, minute=30), id="ingest_shareholding")
    # 殖利率/PER/PBR (TaiwanStockPER) — EOD → 16:30 TW = 08:30 UTC
    scheduler.add_job(_run_ingest_per, CronTrigger(hour=8, minute=30), id="ingest_per")
    # KD/MACD precompute — reads price_daily; run a bit AFTER prices land → 17:00 TW = 09:00 UTC
    scheduler.add_job(_run_compute_indicators, CronTrigger(hour=9, minute=0), id="compute_indicators")
    # ETF NAV / 折溢價 snapshot (TWSE MIS) — finalized after close → 17:00 TW = 09:00 UTC
    scheduler.add_job(_run_ingest_etf_nav, CronTrigger(hour=9, minute=0), id="ingest_etf_nav")
    # Active-ETF holdings snapshot (MoneyDJ, EOD) — feeds the 操作日報 diff → 17:30 TW = 09:30 UTC
    scheduler.add_job(_run_ingest_etf_holdings, CronTrigger(hour=9, minute=30), id="ingest_etf_holdings")
    # Daily scoring at 22:30 TW (14:30 UTC) — after the latest daily source (margin)
    # AND revenue have landed, so scores reflect the full chip picture.
    scheduler.add_job(_run_daily_scoring, CronTrigger(hour=14, minute=30), id="daily_scoring")
    # Weekly quarterly financials: Saturday 14:00 UTC (before Sunday theme/summary jobs)
    scheduler.add_job(_run_weekly_financials, CronTrigger(day_of_week="sat", hour=14, minute=0), id="weekly_financials")
    # Alert check every 30 min during TW trading hours (9:00-13:30 TW = 1:00-5:30 UTC)
    scheduler.add_job(_run_alert_check, CronTrigger(hour="1-5", minute="*/30"), id="alert_check")
    # News refresh every 30 min, all day — the live RSS leading edge changes hourly,
    # and FinMind backfills the current day gradually. Keeps news_daily current.
    scheduler.add_job(_run_ingest_news, CronTrigger(minute="*/30"), id="ingest_news")
    # Weekly theme discovery: Sunday 16:00 UTC (Monday 00:00 TW)
    scheduler.add_job(_run_weekly_themes, CronTrigger(day_of_week="sun", hour=16, minute=0), id="weekly_themes")
    # Weekly AI summaries: Sunday 18:00 UTC (Monday 02:00 TW) — after themes refresh
    scheduler.add_job(_run_weekly_summaries, CronTrigger(day_of_week="sun", hour=18, minute=0), id="weekly_summaries")
    # Weekly supply chain extraction: Sunday 20:00 UTC (Monday 04:00 TW)
    async def _run_supply_chain() -> None:
        try:
            from scripts.extract_supply_chain import run_extraction
            await run_extraction(top_n=SUPPLY_CHAIN_EXTRACTION_TOP_N)
        except Exception as e:
            logger.error("supply_chain_extraction_failed", error=str(e)[:200])
    scheduler.add_job(_run_supply_chain, CronTrigger(day_of_week="sun", hour=20, minute=0), id="weekly_supply_chain")
    # Weekly profile scrape: Monday 10:00 UTC (Monday 18:00 TW)
    async def _run_scrape_profiles() -> None:
        try:
            from scripts.scrape_profiles import scrape_tw_profiles, scrape_us_profiles
            await scrape_tw_profiles()
            await scrape_us_profiles()
        except Exception as e:
            logger.error("scrape_profiles_failed", error=str(e)[:200])
    scheduler.add_job(_run_scrape_profiles, CronTrigger(day_of_week="mon", hour=10, minute=0), id="weekly_profiles")

    # Figure events scan: twice daily at 07:00 and 15:00 UTC (15:00/23:00 TW)
    async def _run_figure_events_scan() -> None:
        try:
            from app.services.platform.figure_event_service import scan_figure_events
            await scan_figure_events()
        except Exception as e:
            logger.error("figure_events_scan_failed", error=str(e)[:200])
    scheduler.add_job(_run_figure_events_scan, CronTrigger(hour="7,15", minute=0), id="figure_events_scan")

    # Run cron jobs in exactly one process. A read-only API worker can't write,
    # and run_scheduler=False lets you scale API workers without each running the
    # cron jobs (which would cause duplicate ingests/scoring).
    scheduler_active = settings.run_scheduler and not duckdb_engine.read_only
    if scheduler_active:
        scheduler.start()
        logger.info("scheduler_started", jobs=["ingest_prices@16:30TW", "ingest_institutional@16:30TW", "ingest_shareholding@16:30TW", "ingest_per@16:30TW", "compute_indicators@17:00TW", "ingest_etf_nav@17:00TW", "ingest_etf_holdings@17:30TW", "ingest_margin@21:30TW", "ingest_revenue@22:00TW", "daily_scoring@22:30TW", "alert_check@every30min", "weekly_themes@sun", "weekly_summaries@sun"])
    else:
        logger.info("scheduler_disabled", run_scheduler=settings.run_scheduler, read_only=duckdb_engine.read_only)

    yield

    # Shutdown
    if scheduler_active:
        scheduler.shutdown(wait=False)
    await finmind.close()
    await cache.close()
    duckdb_engine.close()
    await close_engine()


def create_app() -> FastAPI:
    settings = Settings()

    # Error tracking — no-op unless SENTRY_DSN set + sdk installed.
    from app.core.observability import init_sentry, setup_metrics
    init_sentry(settings)

    app = FastAPI(
        title="Kestrel API",
        description="Taiwan stock analysis platform — FinMind data provider",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Prometheus /metrics — no-op unless enabled + lib installed.
    setup_metrics(app, settings)

    # Unified error envelope for KestrelError / HTTPException / validation /
    # unhandled — replaces the old ErrorHandlerMiddleware (which couldn't catch
    # HTTPException). See app/middleware/exception_handlers.py.
    from app.middleware.exception_handlers import register_exception_handlers
    register_exception_handlers(app)

    # Middleware (order: outermost applied first)
    from app.middleware.cache_headers import CacheHeaderMiddleware
    from app.middleware.hardening import (
        BodySizeLimitMiddleware,
        SecurityHeadersMiddleware,
        TimeoutMiddleware,
    )
    if settings.security_headers_enabled:
        app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CacheHeaderMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(RateLimiterMiddleware, requests_per_minute=settings.api_rate_limit_per_minute)
    app.add_middleware(TimeoutMiddleware, timeout_seconds=settings.request_timeout_seconds)
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_request_bytes)
    # Host-header allowlist (skip when "*" to keep local dev frictionless).
    if settings.allowed_hosts != ["*"]:
        from starlette.middleware.trustedhost import TrustedHostMiddleware
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    setup_cors(app, settings)

    # Routers
    from app.api.v1.router import v1_router

    app.include_router(v1_router, prefix=settings.api_prefix)

    return app


app: FastAPI = create_app()
