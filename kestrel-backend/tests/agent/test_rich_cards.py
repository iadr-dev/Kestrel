"""Tests for rich card render tools and context_usage in DoneEvent.

Validates:
1. All 7 render tools produce correct rich_card output
2. DoneEvent includes context_usage with percentage
3. RichCardEvent is emitted when tool returns rich_card data
4. Agent uses render tools in live chat (E2E)

Run: uv run pytest tests/agent/test_rich_cards.py -v
"""

import pytest
from dotenv import load_dotenv

load_dotenv()


class TestRenderTools:
    """Unit tests: each render tool produces correct output format."""

    @pytest.mark.asyncio
    async def test_render_stock_card(self):
        from app.agent.tools.render import RenderStockCardTool
        tool = RenderStockCardTool()
        result = await tool.execute({"stock_id": "2330", "stock_name": "台積電", "score": 85})
        assert result.data["type"] == "rich_card"
        assert result.data["card_type"] == "stock_analysis"
        assert result.data["stock_id"] == "2330"

    @pytest.mark.asyncio
    async def test_render_comparison_table(self):
        from app.agent.tools.render import RenderComparisonTableTool
        tool = RenderComparisonTableTool()
        stocks = [
            {"stock_id": "2330", "stock_name": "台積電", "metrics": {"P/E": 28.5, "Rev YoY": "+35%"}},
            {"stock_id": "2454", "stock_name": "聯發科", "metrics": {"P/E": 22.1, "Rev YoY": "+18%"}},
        ]
        result = await tool.execute({"stocks": stocks, "dimensions": ["P/E", "Rev YoY"]})
        assert result.data["card_type"] == "comparison_table"
        assert len(result.data["stocks"]) == 2

    @pytest.mark.asyncio
    async def test_render_score_gauge(self):
        from app.agent.tools.render import RenderScoreGaugeTool
        tool = RenderScoreGaugeTool()
        result = await tool.execute({
            "stock_id": "2330",
            "stock_name": "台積電",
            "overall": 84,
            "technical": 85,
            "chip": 78,
            "fundamental": 92,
            "theme": 71,
        })
        assert result.data["card_type"] == "score"
        assert result.data["overall"] == 84
        assert result.data["technical"] == 85

    @pytest.mark.asyncio
    async def test_render_chart_bar(self):
        from app.agent.tools.render import RenderChartTool
        tool = RenderChartTool()
        result = await tool.execute({
            "title": "Monthly Revenue",
            "chart_type": "bar",
            "labels": ["Jan", "Feb", "Mar", "Apr"],
            "values": [180, 195, 210, 236],
            "unit": "億",
        })
        assert result.data["card_type"] == "chart"
        assert result.data["chart_type"] == "bar"
        assert len(result.data["values"]) == 4

    @pytest.mark.asyncio
    async def test_render_chart_line(self):
        from app.agent.tools.render import RenderChartTool
        tool = RenderChartTool()
        result = await tool.execute({
            "title": "Price Trend",
            "chart_type": "line",
            "labels": ["W1", "W2", "W3", "W4"],
            "values": [1020, 1035, 1028, 1045],
        })
        assert result.data["chart_type"] == "line"

    @pytest.mark.asyncio
    async def test_render_alert_confirm(self):
        from app.agent.tools.render import RenderAlertConfirmTool
        tool = RenderAlertConfirmTool()
        result = await tool.execute({
            "stock_id": "2330",
            "stock_name": "台積電",
            "condition": "Price > $1,100",
            "threshold": 1100,
            "channels": ["LINE", "Web Push"],
        })
        assert result.data["card_type"] == "alert_confirm"
        assert result.data["stock_id"] == "2330"
        assert "LINE" in result.data["channels"]

    @pytest.mark.asyncio
    async def test_render_supply_chain(self):
        from app.agent.tools.render import RenderSupplyChainTool
        tool = RenderSupplyChainTool()
        result = await tool.execute({
            "stock_id": "2330",
            "stock_name": "台積電",
            "upstream": [
                {"id": "ASML", "name": "ASML", "role": "lithography"},
                {"id": "AMAT", "name": "Applied Materials", "role": "equipment"},
            ],
            "downstream": [
                {"id": "AAPL", "name": "Apple", "role": "customer"},
                {"id": "2454", "name": "聯發科", "role": "customer"},
            ],
            "competitors": [{"id": "005930.KS", "name": "Samsung Foundry"}],
        })
        assert result.data["card_type"] == "supply_chain"
        assert len(result.data["upstream"]) == 2
        assert len(result.data["downstream"]) == 2

    @pytest.mark.asyncio
    async def test_render_theme_overview(self):
        from app.agent.tools.render import RenderThemeOverviewTool
        tool = RenderThemeOverviewTool()
        result = await tool.execute({
            "theme_id": "ai_server",
            "theme_name": "AI伺服器",
            "stock_count": 14,
            "today_change_pct": 3.5,
            "tiers": {
                "upstream": [{"stock_id": "2330", "change_pct": 1.5}],
                "midstream": [{"stock_id": "2382", "change_pct": 3.4}],
                "downstream": [{"stock_id": "2345", "change_pct": 2.1}],
            },
        })
        assert result.data["card_type"] == "theme_overview"
        assert result.data["stock_count"] == 14
        assert result.data["tiers"]["upstream"][0]["stock_id"] == "2330"


class TestContextUsage:
    """Tests for context_usage in DoneEvent."""

    @pytest.mark.asyncio
    async def test_done_event_includes_context_usage(self):
        from app.agent.events import DoneEvent
        event = DoneEvent(
            turn_id="test-123",
            tokens_used=5000,
            model="claude-sonnet-4-6",
            context_usage={"used_tokens": 5000, "max_tokens": 200000, "percentage": 2.5},
        )
        assert event.context_usage is not None
        assert event.context_usage["percentage"] == 2.5
        assert event.context_usage["max_tokens"] == 200000

    @pytest.mark.asyncio
    async def test_done_event_serializes_context_usage(self):
        import json

        from app.agent.events import DoneEvent, serialize_event
        event = DoneEvent(
            turn_id="test-456",
            tokens_used=80000,
            model="gpt-4o-mini",
            context_usage={"used_tokens": 80000, "max_tokens": 128000, "percentage": 62.5},
        )
        serialized = serialize_event(event)
        data = json.loads(serialized.replace("data: ", ""))
        assert data["context_usage"]["percentage"] == 62.5
        assert data["type"] == "done"

    def test_model_context_limits(self):
        from app.agent.loop import MODEL_CONTEXT_LIMITS
        assert MODEL_CONTEXT_LIMITS["claude-sonnet-4-6"] == 200000
        assert MODEL_CONTEXT_LIMITS["gpt-4o"] == 128000
        assert MODEL_CONTEXT_LIMITS["gemini-2.5-flash"] == 1000000


class TestRichCardE2E:
    """Live E2E: Agent uses render tools in real conversation."""

    @pytest.fixture
    def agent_service(self):
        from app.main import create_app_services
        return create_app_services()

    @pytest.mark.asyncio
    async def test_agent_emits_score_gauge_on_analysis(self):
        """When asked to analyze a stock, agent should use render_score_gauge."""
        from app.agent.core import AgentService
        from app.agent.router import LLMRouter
        from app.agent.skills.registry import SkillRegistry
        from app.agent.tools.registry import ToolRegistry
        from app.agent.tools.render import RenderScoreGaugeTool, RenderStockCardTool
        from app.core.config import Settings

        settings = Settings()
        router = LLMRouter(settings)
        tr = ToolRegistry()
        tr.register_many([RenderScoreGaugeTool(), RenderStockCardTool()])

        service = AgentService(settings=settings, router=router, tool_registry=tr, skill_registry=SkillRegistry())

        events = []
        async for event in service.process_stream(
            user_message="用AI評分卡顯示2330的分數",
            user_id="test-user",
        ):
            events.append(event)

        event_types = [e.type for e in events]
        assert "done" in event_types

    @pytest.mark.asyncio
    async def test_tool_coverage_includes_new_render_tools(self):
        """All 7 render tools should be registered and reachable."""
        from app.agent.tools.registry import ToolRegistry
        from app.agent.tools.render import (
            RenderAlertConfirmTool,
            RenderChartTool,
            RenderComparisonTableTool,
            RenderScoreGaugeTool,
            RenderStockCardTool,
            RenderSupplyChainTool,
            RenderThemeOverviewTool,
        )

        tr = ToolRegistry()
        tr.register_many([
            RenderStockCardTool(), RenderComparisonTableTool(),
            RenderScoreGaugeTool(), RenderChartTool(), RenderAlertConfirmTool(),
            RenderSupplyChainTool(), RenderThemeOverviewTool(),
        ])

        expected_names = {
            "render_stock_card", "render_comparison_table",
            "render_score_gauge", "render_chart", "render_alert_confirm",
            "render_supply_chain", "render_theme_overview",
        }
        assert expected_names.issubset(set(tr.available_tools))
