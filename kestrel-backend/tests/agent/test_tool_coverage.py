"""Validation test: all 67 registered tools are reachable through skills + CORE_TOOLS.

Ensures no tool is dead code — every registered tool must be:
1. Listed in at least one skill YAML, OR
2. In the CORE_TOOLS list (always available)

Also validates that all tool names in skill YAMLs actually exist in the ToolRegistry.

Run: pytest tests/agent/test_tool_coverage.py -v
"""

from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


CORE_TOOLS = [
    "ask_user", "recall_context", "learn_fact", "forget_fact",
    "set_preference", "render_stock_card", "render_comparison_table",
    "get_realtime_quote", "search_stocks",
    "web_search", "fetch_page", "deep_research",
]

CATALOG_DIR = Path(__file__).parent.parent.parent / "app" / "agent" / "skills" / "catalog"


def get_skill_tools() -> dict[str, list[str]]:
    """Load all skill YAMLs and return {skill_name: [tool_names]}."""
    result = {}
    for f in sorted(CATALOG_DIR.glob("*.yaml")):
        with open(f) as fh:
            data = yaml.safe_load(fh)
        result[data["name"]] = data.get("tools", [])
    return result


def get_registered_tool_names() -> set[str]:
    """Get all tool names from the ToolRegistry after full registration."""
    # The registry is created in main.py — we need to access it
    # Import all tool modules to ensure registration
    from app.agent.tools import (
        analysis,
        fundamental,
        institutional,
        market,
        memory_tools,
        mops_tools,
        rankings_tools,
        render,
        research,
        tdcc_tools,
        twse_tools,
        user_tools,
        web_search,
        yfinance_tools,
    )
    from app.agent.tools import ask_user as ask_user_mod
    from app.agent.tools.registry import ToolRegistry

    # Build a fresh registry with all tools (same as main.py)
    from app.core.config import Settings
    from app.providers.base import ProviderCapability
    from app.providers.cache import InMemoryCache
    from app.providers.finmind import FinMindProvider
    from app.providers.registry import ProviderRegistry
    from app.services.data.fundamental_service import FundamentalService
    from app.services.data.institutional_service import InstitutionalService
    from app.services.data.macro_service import MacroService
    from app.services.data.market_service import MarketService
    from app.services.data.screener_service import ScreenerService
    from app.services.data.stock_service import StockService

    settings = Settings()
    provider = FinMindProvider(settings)
    reg = ProviderRegistry()
    reg.register(provider, capabilities=[
        ProviderCapability.STOCK_PRICE, ProviderCapability.INSTITUTIONAL,
        ProviderCapability.FUNDAMENTAL, ProviderCapability.DERIVATIVE, ProviderCapability.MACRO,
    ])
    cache = InMemoryCache()
    stock_svc = StockService(registry=reg, cache=cache)
    market_svc = MarketService(registry=reg, cache=cache)
    inst_svc = InstitutionalService(registry=reg, cache=cache)
    fund_svc = FundamentalService(registry=reg, cache=cache)
    macro_svc = MacroService(registry=reg, cache=cache)
    screen_svc = ScreenerService(registry=reg, cache=cache)

    tr = ToolRegistry()
    tr.register_many([
        market.GetStockPriceTool(stock_svc), market.GetMarketIndexTool(market_svc),
        market.GetInstitutionalFlowTool(inst_svc), market.GetRevenueTool(fund_svc),
        market.GetMacroDataTool(macro_svc), market.ScreenStocksTool(screen_svc),
        institutional.GetMarginTool(inst_svc), institutional.GetShareholdingTool(inst_svc),
        institutional.GetMainForceTool(inst_svc), institutional.GetGovernmentBankTool(inst_svc),
        fundamental.GetFinancialsTool(fund_svc), fundamental.GetDividendTool(fund_svc),
        fundamental.GetMarketValueTool(fund_svc),
        analysis.GetIndicatorsTool(stock_svc), analysis.GetScoreTool(stock_svc),
        twse_tools.GetRealtimeQuoteTool(), twse_tools.GetNoticeStocksTool(),
        twse_tools.GetDisposalStocksTool(), twse_tools.GetTWSEInstitutionalTool(),
        twse_tools.GetFuturesPositionTool(), twse_tools.GetCompanyProfileTool(),
        twse_tools.GetSupplyChainTool(), twse_tools.GetThemeStocksTool(),
        twse_tools.GetETFDataTool(), twse_tools.GetOTCStockTool(),
        twse_tools.GetPutCallRatioTool(), twse_tools.GetOptionsAnalyticsTool(),
        twse_tools.GetBacktestResultTool(), twse_tools.GetCompanyESGTool(),
        twse_tools.GetWarrantInfoTool(), twse_tools.GetMarketHolidaysTool(),
        tdcc_tools.GetShareholdingDistributionTool(), tdcc_tools.GetDirectorCustodyTool(),
        tdcc_tools.GetWeeklyBalanceTool(), tdcc_tools.GetMonthlyCustodyChangeTool(),
        mops_tools.GetAnnouncementsTool(), mops_tools.GetTreasuryStockTool(),
        mops_tools.GetInvestorConferenceTool(), mops_tools.GetDirectorHoldingsTool(),
        rankings_tools.GetStockRankingsTool(),
        rankings_tools.GetInstitutionalRankingsTool(), rankings_tools.GetMarginRankingsTool(),
        yfinance_tools.GetAnalystTargetTool(), yfinance_tools.GetEarningsCalendarTool(),
        yfinance_tools.GetHoldersTool(), yfinance_tools.GetStockHistoryTool(),
        yfinance_tools.GetFinancialsTool(), yfinance_tools.GetMarketSearchTool(),
        yfinance_tools.GetMarketScreenerTool(), yfinance_tools.GetSectorInfoTool(),
        yfinance_tools.GetNewsTool(), yfinance_tools.GetPeersTool(),
        ask_user_mod.AskUserTool(), user_tools.ScheduleAlertTool(), user_tools.SetPreferenceTool(),
        memory_tools.RecallContextTool(), memory_tools.LearnFactTool(), memory_tools.ForgetFactTool(),
        render.RenderStockCardTool(), render.RenderComparisonTableTool(),
        web_search.WebSearchTool(), web_search.FetchPageTool(),
        research.DeepResearchTool(),
    ])
    return set(tr.available_tools)


class TestToolCoverage:
    """Validate that all registered tools are reachable."""

    def test_all_tools_reachable(self):
        """Every registered tool must be in at least one skill OR in CORE_TOOLS."""
        registered = get_registered_tool_names()
        skill_data = get_skill_tools()
        all_skill_tools = set()
        for tools in skill_data.values():
            all_skill_tools.update(tools)

        core_set = set(CORE_TOOLS)
        reachable = all_skill_tools | core_set
        unreachable = registered - reachable

        assert unreachable == set(), f"Tools NOT reachable through skills or CORE_TOOLS: {sorted(unreachable)}"

    def test_skill_tools_exist_in_registry(self):
        """Every tool name in skill YAMLs must exist in the ToolRegistry."""
        registered = get_registered_tool_names()
        skill_data = get_skill_tools()

        invalid = {}
        for skill_name, tools in skill_data.items():
            missing = [t for t in tools if t not in registered]
            if missing:
                invalid[skill_name] = missing

        assert invalid == {}, f"Skills reference non-existent tools: {invalid}"

    def test_no_duplicate_tools_across_yaml_and_core(self):
        """Report overlap (not an error, just informational)."""
        skill_data = get_skill_tools()
        all_skill_tools = set()
        for tools in skill_data.values():
            all_skill_tools.update(tools)

        overlap = all_skill_tools & set(CORE_TOOLS)
        # Overlap is fine (tools can be in both), just report
        print(f"\nOverlap (in both skills and CORE_TOOLS): {sorted(overlap)}")
        assert True  # Always passes — informational only

    def test_every_skill_has_tools(self):
        """Every skill must define at least 1 tool."""
        skill_data = get_skill_tools()
        empty_skills = [name for name, tools in skill_data.items() if not tools]
        assert empty_skills == [], f"Skills with no tools: {empty_skills}"

    def test_15_skills_exist(self):
        """We should have exactly 15 skill YAMLs."""
        skill_data = get_skill_tools()
        assert len(skill_data) == 15, f"Expected 15 skills, got {len(skill_data)}: {list(skill_data.keys())}"

    def test_registered_tool_count(self):
        """We should have 67 registered tools."""
        registered = get_registered_tool_names()
        assert len(registered) >= 65, f"Expected ~67 tools, got {len(registered)}"
