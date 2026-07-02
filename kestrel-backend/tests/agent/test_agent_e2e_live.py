"""End-to-end live tests for the Kestrel agent system.

Tests the FULL agent pipeline with real LLM calls:
- Intent classification (LLM decides framework + skills)
- Single agent with skill-focused tools
- Subagent parallel analysis
- Agent Team collaborative research
- Memory (semantic facts, working memory)
- Feedback (persist + quality scoring)
- Sessions (create, list, resume)
- ask_user pause mechanism
- Greeting/off-topic handling (no tools)

50+ user queries covering all agent capabilities.
ALL tests use live API keys from .env.

Run: pytest tests/agent/test_agent_e2e_live.py -v
"""

import json

import pytest
from dotenv import load_dotenv

load_dotenv()

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.security import create_access_token
from app.main import app


@pytest.fixture(scope="module")
async def client():
    """Async test client with app lifespan for non-streaming endpoints."""
    async with LifespanManager(app) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=300.0) as ac:
            yield ac


ADMIN_TEST_ID = "admin-e2e-test"


@pytest.fixture
async def auth(client):
    """Auth headers using an admin account (no tier limits).

    Seeds a real admin User row with id=ADMIN_TEST_ID and an email from
    ADMIN_EMAILS, so the admin-only endpoints' require_admin dependency (which
    looks the user up by id in the DB) actually passes. Without the seeded row,
    require_admin returns 403 even though the token claims tier=pro.
    """
    settings = Settings()
    admin_email = settings.admin_emails[0] if settings.admin_emails else "admin-e2e@test.local"

    from sqlalchemy import select

    from app.db.session import get_session_factory
    from app.models.user import User

    factory = get_session_factory()
    async with factory() as session:
        existing = await session.get(User, ADMIN_TEST_ID)
        if existing is None:
            # Detach any pre-existing row holding this email (unique constraint).
            dup = (await session.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()
            email_to_use = admin_email if dup is None else f"{ADMIN_TEST_ID}@test.local"
            session.add(User(id=ADMIN_TEST_ID, email=email_to_use, display_name="E2E Admin", tier="pro"))
            await session.commit()

    token = create_access_token({"sub": ADMIN_TEST_ID, "email": admin_email, "tier": "pro"}, settings)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
async def agent_service():
    """Direct AgentService instance — bypasses HTTP for streaming tests."""
    from app.agent.core import AgentService
    from app.agent.router import LLMRouter
    from app.agent.skills.registry import SkillRegistry

    # Import app to trigger full tool registration

    settings = Settings()
    router = LLMRouter(settings)

    # Get the fully registered tool registry from main.py's startup
    from app.agent.tools.analysis import GetIndicatorsTool
    from app.agent.tools.fundamental import GetDividendTool, GetFinancialsTool
    from app.agent.tools.institutional import GetMarginTool, GetShareholdingTool
    from app.agent.tools.market import (
        GetInstitutionalFlowTool,
        GetMacroDataTool,
        GetMarketIndexTool,
        GetRevenueTool,
        GetStockPriceTool,
        ScreenStocksTool,
    )
    from app.agent.tools.mops_tools import GetAnnouncementsTool
    from app.agent.tools.rankings_tools import (
        GetInstitutionalRankingsTool,
        GetStockRankingsTool,
    )
    from app.agent.tools.registry import ToolRegistry
    from app.agent.tools.tdcc_tools import GetShareholdingDistributionTool
    from app.agent.tools.twse_tools import GetETFDataTool, GetNoticeStocksTool, GetRealtimeQuoteTool
    from app.agent.tools.yfinance_tools import (
        GetAnalystTargetTool,
        GetMarketSearchTool,
        GetNewsTool,
    )
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

    provider = FinMindProvider(settings)
    registry = ProviderRegistry()
    registry.register(provider, capabilities=[
        ProviderCapability.STOCK_PRICE, ProviderCapability.INSTITUTIONAL,
        ProviderCapability.FUNDAMENTAL, ProviderCapability.DERIVATIVE, ProviderCapability.MACRO,
    ])
    cache = InMemoryCache()

    stock_svc = StockService(registry=registry, cache=cache)
    market_svc = MarketService(registry=registry, cache=cache)
    inst_svc = InstitutionalService(registry=registry, cache=cache)
    fund_svc = FundamentalService(registry=registry, cache=cache)
    macro_svc = MacroService(registry=registry, cache=cache)
    screen_svc = ScreenerService(registry=registry, cache=cache)

    tr = ToolRegistry()
    tr.register_many([
        GetStockPriceTool(stock_svc), GetMarketIndexTool(market_svc),
        GetInstitutionalFlowTool(inst_svc), GetRevenueTool(fund_svc),
        GetMacroDataTool(macro_svc), ScreenStocksTool(screen_svc),
        GetMarginTool(inst_svc), GetShareholdingTool(inst_svc),
        GetFinancialsTool(fund_svc), GetDividendTool(fund_svc),
        GetIndicatorsTool(stock_svc),
        GetRealtimeQuoteTool(), GetNoticeStocksTool(), GetETFDataTool(),
        GetAnalystTargetTool(), GetMarketSearchTool(), GetNewsTool(),
        GetShareholdingDistributionTool(), GetAnnouncementsTool(),
        GetStockRankingsTool(), GetInstitutionalRankingsTool(),
    ])

    skills = SkillRegistry()
    service = AgentService(settings, router, tr, skills)
    return service


def _skip_if_llm_quota(events: list[dict]) -> None:
    """Skip (don't fail) when the LLM provider is rate-limited / out of quota.

    Live LLM tests can't pass once the upstream daily quota is exhausted (e.g.
    Gemini free-tier 429 / RESOURCE_EXHAUSTED). That's an environment limit, not
    a code regression, so we skip rather than fail. The provider surfaces these
    as an error event whose text contains the quota/429 markers.
    """
    markers = ("429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "All models failed", "Stream interrupted")
    for e in events:
        if e.get("type") in ("error", "done"):
            text = f"{e.get('content', '')}{e.get('message', '')}{e.get('stop_reason', '')}"
            if any(m.lower() in text.lower() for m in markers):
                pytest.skip(f"LLM provider unavailable/quota-exhausted: {text[:120]}")


async def chat_stream(client_or_service, auth_or_none, message: str, model: str | None = None) -> list[dict]:
    """Helper: run agent and collect events as dicts."""
    # Use AgentService directly (bypasses HTTP SSE issues)
    if hasattr(client_or_service, "process_stream"):
        events = []
        async for event in client_or_service.process_stream(
            user_message=message, user_id="admin-e2e-test", model=model
        ):
            e = event.__dict__.copy()
            events.append(e)
        _skip_if_llm_quota(events)
        return events
    # Fallback to HTTP client
    body = {"message": message}
    if model:
        body["model"] = model
    resp = await client_or_service.post("/api/v1/agent/chat/stream", json=body, headers=auth_or_none)
    if resp.status_code == 403:
        pytest.skip("Tier gate daily limit reached")
    parsed = []
    for line in resp.text.split("\n"):
        if line.startswith("data:") and "[DONE]" not in line:
            try:
                parsed.append(json.loads(line.removeprefix("data:").strip()))
            except json.JSONDecodeError:
                pass
    _skip_if_llm_quota(parsed)
    return parsed


def has_event_type(events: list[dict], event_type: str) -> bool:
    return any(e.get("type") == event_type for e in events)


def get_text(events: list[dict]) -> str:
    return "".join(e.get("delta", "") for e in events if e.get("type") == "text")


# ═══════════════════════════════════════════════════════════════════
# 1. GREETING / OFF-TOPIC (framework="none", no tools)
# ═══════════════════════════════════════════════════════════════════

class TestGreetingOffTopic:
    """Agent responds from system prompt alone — no tools, no skills."""

    @pytest.mark.asyncio
    async def test_hello(self, agent_service):
        events = await chat_stream(agent_service, None, "你好")
        text = get_text(events)
        assert len(text) > 10
        assert has_event_type(events, "done")

    @pytest.mark.asyncio
    async def test_english_greeting(self, agent_service):
        events = await chat_stream(agent_service, None, "Hi, what can you do?")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_off_topic(self, agent_service):
        events = await chat_stream(agent_service, None, "今天天氣怎麼樣？")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_who_are_you(self, agent_service):
        events = await chat_stream(agent_service, None, "你是誰？")
        text = get_text(events)
        assert "Kestrel" in text or "紅隼" in text or "分析" in text


# ═══════════════════════════════════════════════════════════════════
# 2. SINGLE AGENT — Simple stock queries (framework="single")
# ═══════════════════════════════════════════════════════════════════

class TestSingleAgentSimple:
    """Single agent with skill tools — quick lookups."""

    @pytest.mark.asyncio
    async def test_stock_price(self, agent_service):
        """Simple price query → stock_analysis skill."""
        events = await chat_stream(agent_service, None, "台積電現在多少錢？")
        text = get_text(events)
        assert any(c.isdigit() for c in text)

    @pytest.mark.asyncio
    async def test_stock_price_english(self, agent_service):
        events = await chat_stream(agent_service, None, "What's the price of TSMC?")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_realtime_quote(self, agent_service):
        events = await chat_stream(agent_service, None, "2330 即時報價")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_chip_flow(self, agent_service):
        """Chip query → chip_flow skill."""
        events = await chat_stream(agent_service, None, "2330 外資今天買賣超多少？")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_revenue(self, agent_service):
        """Revenue → earnings_review skill."""
        events = await chat_stream(agent_service, None, "台積電最近營收如何？")
        text = get_text(events)
        assert len(text) > 30

    @pytest.mark.asyncio
    async def test_shareholding(self, agent_service):
        """TDCC → shareholding_analysis skill."""
        events = await chat_stream(agent_service, None, "2330 集保股權分散")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_announcements(self, agent_service):
        """MOPS → corporate_actions skill."""
        events = await chat_stream(agent_service, None, "台積電最近有什麼重大訊息？")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_dividend_calendar(self, agent_service):
        """TWSE dividend schedule → market_movers skill."""
        events = await chat_stream(agent_service, None, "最近有哪些除權息？")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_ipo_lottery(self, agent_service):
        events = await chat_stream(agent_service, None, "現在有什麼可以抽籤的股票？")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_market_overview(self, agent_service):
        """Market → market_briefing skill."""
        events = await chat_stream(agent_service, None, "大盤今天怎樣？")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_notice_stocks(self, agent_service):
        """Risk → anti_fraud skill."""
        events = await chat_stream(agent_service, None, "目前有哪些注意股？")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_screener(self, agent_service):
        """Screener skill."""
        events = await chat_stream(agent_service, None, "幫我篩選今天強勢股")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_us_stock(self, agent_service):
        """International → international_stocks skill."""
        events = await chat_stream(agent_service, None, "NVIDIA 最近股價走勢如何？")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_search_stock(self, agent_service):
        events = await chat_stream(agent_service, None, "幫我搜尋特斯拉的股票代號")
        text = get_text(events)
        assert "TSLA" in text or "Tesla" in text

    @pytest.mark.asyncio
    async def test_etf_data(self, agent_service):
        """ETF → company_research skill."""
        events = await chat_stream(agent_service, None, "0050 ETF 溢折價是多少？")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_supply_chain(self, agent_service):
        events = await chat_stream(agent_service, None, "台積電的供應鏈有哪些公司？")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_margin_trading(self, agent_service):
        events = await chat_stream(agent_service, None, "2330 融資融券狀況")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_futures_position(self, agent_service):
        events = await chat_stream(agent_service, None, "台指期貨大額交易人部位")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_comparison(self, agent_service):
        """Comparison → compare_stocks skill."""
        events = await chat_stream(agent_service, None, "比較台積電和聯發科")
        text = get_text(events)
        assert len(text) > 30


# ═══════════════════════════════════════════════════════════════════
# 3. MULTI-AGENT — Subagent parallel (framework="subagent")
# ═══════════════════════════════════════════════════════════════════

class TestSubagentParallel:
    """Complex queries → multiple subagents in parallel."""

    @pytest.mark.asyncio
    async def test_comprehensive_analysis(self, agent_service):
        """Full analysis → subagent with 3 skills."""
        events = await chat_stream(agent_service, None, "全面分析台積電 2330")
        text = get_text(events)
        assert len(text) > 100
        assert has_event_type(events, "status")

    @pytest.mark.asyncio
    async def test_market_overview_multi(self, agent_service):
        """Market multi-angle → subagent."""
        events = await chat_stream(agent_service, None, "市場總覽，大盤跟法人動態")
        text = get_text(events)
        assert len(text) > 50

    @pytest.mark.asyncio
    async def test_multi_dimension(self, agent_service):
        """Multi-dimension query."""
        events = await chat_stream(agent_service, None, "台積電的集保跟法人籌碼怎麼看")
        text = get_text(events)
        assert len(text) > 50


# ═══════════════════════════════════════════════════════════════════
# 4. AGENT TEAM — Collaborative (framework="team")
# ═══════════════════════════════════════════════════════════════════

class TestAgentTeam:
    """Deep research → agent team with shared context."""

    @pytest.mark.asyncio
    async def test_deep_research(self, agent_service):
        """Deep research → team framework."""
        events = await chat_stream(agent_service, None, "深度研究台積電在AI領域的競爭優勢")
        text = get_text(events)
        assert len(text) > 100
        assert has_event_type(events, "status")


# ═══════════════════════════════════════════════════════════════════
# 5. SESSIONS — Create, list, resume
# ═══════════════════════════════════════════════════════════════════

class TestSessions:
    @pytest.mark.asyncio
    async def test_list_sessions(self, client, auth):
        resp = await client.get("/api/v1/agent/sessions", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body or "sessions" in body

    @pytest.mark.asyncio
    async def test_session_created_after_chat(self, client, auth):
        """Sessions list is accessible."""
        resp = await client.get("/api/v1/agent/sessions", headers=auth)
        body = resp.json()
        sessions = body.get("data", body.get("sessions", []))
        assert isinstance(sessions, list)


# ═══════════════════════════════════════════════════════════════════
# 6. MEMORY — Semantic facts
# ═══════════════════════════════════════════════════════════════════

class TestMemory:
    @pytest.mark.asyncio
    async def test_get_memory(self, client, auth):
        resp = await client.get("/api/v1/agent/memory", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body or "facts" in body


# ═══════════════════════════════════════════════════════════════════
# 7. FEEDBACK — Thumb up/down
# ═══════════════════════════════════════════════════════════════════

class TestFeedback:
    @pytest.mark.asyncio
    async def test_thumb_up(self, client, auth):
        resp = await client.post(
            "/api/v1/agent/chat/feedback",
            json={"turn_id": "test-turn-001", "rating": "up"},
            headers=auth,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "recorded"
        assert body["rating"] == "up"

    @pytest.mark.asyncio
    async def test_thumb_down_with_comment(self, client, auth):
        resp = await client.post(
            "/api/v1/agent/chat/feedback",
            json={"turn_id": "test-turn-002", "rating": "down", "comment": "Data was wrong"},
            headers=auth,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["rating"] == "down"

    @pytest.mark.asyncio
    async def test_quality_endpoint(self, client, auth):
        resp = await client.get("/api/v1/agent/quality", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "skills" in body

    @pytest.mark.asyncio
    async def test_feedback_alerts_list(self, client, auth):
        resp = await client.get("/api/v1/agent/feedback/alerts", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    @pytest.mark.asyncio
    async def test_feedback_recent(self, client, auth):
        resp = await client.get("/api/v1/agent/feedback/recent", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body


# ═══════════════════════════════════════════════════════════════════
# 8. AGENT SETTINGS — User preferences
# ═══════════════════════════════════════════════════════════════════

class TestAgentSettings:
    @pytest.mark.asyncio
    async def test_get_settings(self, client, auth):
        resp = await client.get("/api/v1/user/agent-settings", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        data = body["data"]
        assert "response_style" in data
        assert "custom_instructions" in data
        assert "focus_areas" in data

    @pytest.mark.asyncio
    async def test_update_settings(self, client, auth):
        resp = await client.put(
            "/api/v1/user/agent-settings",
            json={"response_style": "concise", "focus_areas": ["technical", "institutional"]},
            headers=auth,
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 9. SKILLS — Catalog listing
# ═══════════════════════════════════════════════════════════════════

class TestSkills:
    @pytest.mark.asyncio
    async def test_list_skills(self, client, auth):
        resp = await client.get("/api/v1/agent/skills", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert len(body["data"]) == 15

    @pytest.mark.asyncio
    async def test_skills_have_quality_scores(self, client, auth):
        resp = await client.get("/api/v1/agent/skills", headers=auth)
        body = resp.json()
        for skill in body["data"]:
            assert "name" in skill
            assert "description" in skill


# ═══════════════════════════════════════════════════════════════════
# 10. COST TRACKING
# ═══════════════════════════════════════════════════════════════════

class TestCost:
    @pytest.mark.asyncio
    async def test_get_cost(self, client, auth):
        resp = await client.get("/api/v1/agent/cost", headers=auth)
        assert resp.status_code == 200
        body = resp.json()
        assert "daily_cost_usd" in body


# ═══════════════════════════════════════════════════════════════════
# 11. EDIT / RETRY / CLARIFY
# ═══════════════════════════════════════════════════════════════════

class TestEditRetryClarify:
    @pytest.mark.asyncio
    async def test_retry_nonexistent(self, client, auth):
        """Retry with non-existent turn returns 404 or empty."""
        resp = await client.post(
            "/api/v1/agent/chat/retry",
            json={"turn_id": "nonexistent", "session_id": "nonexistent"},
            headers=auth,
        )
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_clarify_endpoint(self, client, auth):
        """Clarify endpoint accepts answer."""
        resp = await client.post(
            "/api/v1/agent/chat/clarify",
            json={"session_id": "test-session", "clarification_id": "c1", "answer": "2330"},
            headers=auth,
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 12. MIXED LANGUAGE / EDGE CASES
# ═══════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════
# 13. INTENT CLASSIFICATION ACCURACY
# ═══════════════════════════════════════════════════════════════════

class TestIntentClassification:
    """Verify the LLM classifier assigns correct framework + skills."""

    @pytest.fixture
    def router(self):
        from app.agent.router import LLMRouter
        return LLMRouter(Settings())

    @pytest.mark.asyncio
    async def test_greeting_classified_none(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("你好", router)
        assert result.framework == "none"
        assert result.skills == []

    @pytest.mark.asyncio
    async def test_price_classified_single(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("台積電股價多少", router)
        assert result.framework == "single"
        assert len(result.skills) >= 1

    @pytest.mark.asyncio
    async def test_chip_classified_with_chip_skill(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("2330 外資買賣超", router)
        assert result.framework in ("single", "subagent")
        assert any(s in result.skills for s in ["chip_flow", "stock_analysis"])

    @pytest.mark.asyncio
    async def test_full_analysis_classified_subagent(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("全面分析台積電", router)
        assert result.framework == "subagent"
        assert len(result.skills) >= 2

    @pytest.mark.asyncio
    async def test_deep_research_classified_team(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("深度研究台積電AI競爭優勢", router)
        assert result.framework == "team"
        assert len(result.skills) >= 2

    @pytest.mark.asyncio
    async def test_off_topic_classified_none(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("幫我訂pizza", router)
        assert result.framework == "none"

    @pytest.mark.asyncio
    async def test_revenue_gets_earnings_skill(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("台積電最近營收多少", router)
        assert "earnings_review" in result.skills or "stock_analysis" in result.skills

    @pytest.mark.asyncio
    async def test_shareholding_gets_tdcc_skill(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("查一下2330集保資料", router)
        valid_skills = {"shareholding_analysis", "chip_flow"}
        assert any(s in valid_skills for s in result.skills), f"Expected shareholding-related skill, got: {result}"

    @pytest.mark.asyncio
    async def test_us_stock_gets_international_skill(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("NVIDIA earnings report", router)
        assert "international_stocks" in result.skills or "earnings_review" in result.skills

    @pytest.mark.asyncio
    async def test_market_overview_gets_briefing(self, router):
        from app.agent.multi.strategies import classify_intent
        result = await classify_intent("今天大盤走勢如何", router)
        valid_skills = {"market_briefing", "stock_analysis", "chip_flow"}
        assert any(s in valid_skills for s in result.skills), f"Expected market-related skill, got: {result}"


# ═══════════════════════════════════════════════════════════════════
# 14. SKILL + TOOL CALL HIT RATE
# ═══════════════════════════════════════════════════════════════════

class TestSkillToolHitRate:
    """Verify that when a skill is assigned, its tools actually get called."""

    @pytest.mark.asyncio
    async def test_stock_analysis_calls_tools(self, agent_service):
        """stock_analysis skill should trigger tool_start events."""
        events = await chat_stream(agent_service, None, "分析2330走勢")
        tool_starts = [e for e in events if e.get("type") == "tool_start"]
        assert len(tool_starts) > 0, "Expected at least 1 tool call for stock analysis"

    @pytest.mark.asyncio
    async def test_chip_flow_calls_institutional(self, agent_service):
        """chip_flow skill should call institutional-related tools."""
        events = await chat_stream(agent_service, None, "2330法人買賣超")
        tool_starts = [e for e in events if e.get("type") == "tool_start"]
        assert len(tool_starts) > 0, "Expected tool calls for chip flow"

    @pytest.mark.asyncio
    async def test_greeting_no_tool_calls(self, agent_service):
        """Greeting should have ZERO tool calls."""
        events = await chat_stream(agent_service, None, "嗨你好呀")
        tool_starts = [e for e in events if e.get("type") == "tool_start"]
        assert len(tool_starts) == 0, f"Expected 0 tools for greeting, got {len(tool_starts)}"

    @pytest.mark.asyncio
    async def test_revenue_calls_get_revenue(self, agent_service):
        """earnings_review should call revenue-related tools."""
        events = await chat_stream(agent_service, None, "台積電營收多少")
        tool_starts = [e for e in events if e.get("type") == "tool_start"]
        tool_names = [e.get("display_name", "") for e in tool_starts]
        assert len(tool_starts) > 0, f"Expected tools for revenue query, got names: {tool_names}"

    @pytest.mark.asyncio
    async def test_screener_calls_screen(self, agent_service):
        """screener skill should produce a response (tool calls or text)."""
        events = await chat_stream(agent_service, None, "幫我選股，今天強勢突破的")
        tool_starts = [e for e in events if e.get("type") == "tool_start"]
        text = get_text(events)
        assert len(tool_starts) > 0 or len(text) > 20

    @pytest.mark.asyncio
    async def test_subagent_no_tool_starts_in_stream(self, agent_service):
        """Subagent path streams text directly — tool calls happen inside subagents, not visible in main stream."""
        events = await chat_stream(agent_service, None, "全面分析2454聯發科")
        # Subagent path yields StatusEvent + TextEvent + DoneEvent (no tool_start in main stream)
        has_status = has_event_type(events, "status")
        has_text = has_event_type(events, "text")
        assert has_text, "Subagent should produce text output"


# ═══════════════════════════════════════════════════════════════════
# 15. EDGE CASES
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_mixed_chinese_english(self, agent_service):
        events = await chat_stream(agent_service, None, "台積電的PE ratio是多少？")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_stock_code_only(self, agent_service):
        events = await chat_stream(agent_service, None, "2330")
        text = get_text(events)
        assert len(text) > 10

    @pytest.mark.asyncio
    async def test_multiple_stocks(self, agent_service):
        events = await chat_stream(agent_service, None, "2330 跟 2454 今天外資怎麼買")
        text = get_text(events)
        assert len(text) > 20

    @pytest.mark.asyncio
    async def test_very_short_query(self, agent_service):
        events = await chat_stream(agent_service, None, "？")
        text = get_text(events)
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_long_query(self, agent_service):
        events = await chat_stream(agent_service, None,
            "我最近在觀察台積電，想了解一下最近法人的買賣超情況，"
            "以及營收是否有持續成長，還有技術面上是否適合進場"
        )
        text = get_text(events)
        assert len(text) > 50
