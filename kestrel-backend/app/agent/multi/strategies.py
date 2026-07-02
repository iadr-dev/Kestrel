"""Dynamic strategy dispatch — LLM classifies intent, assigns skills to agents.

Replaces hardcoded keyword matching + ROLE_CONFIG with:
1. LLM classifier decides: framework (single/subagent/team/none) + which skills
2. Skills provide the tools + instructions for each agent
3. SubagentRunner/AgentTeam use skill definitions directly
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from app.agent.multi.subagent import SubagentTask
from app.core.logging import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from app.agent.multi.team import Teammate, TeamTask
    from app.agent.router import LLMRouter
    from app.agent.skills.registry import SkillRegistry

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "strategy_router.md"


@dataclass
class DispatchResult:
    """Result of LLM-based intent classification."""
    framework: str  # "single" | "subagent" | "team" | "none"
    skills: list[str] = field(default_factory=list)


# Priority: chatanywhere gpt-4o-mini (free, 200/day, reliable JSON) → deepseek
# (NVIDIA NIM, free) → openrouter/free → gemini (free tier, 429s under burst) →
# claude-haiku (paid, always-on safety net). All free options exhaust before paid.
CLASSIFIER_MODELS = ["chatanywhere/gpt-4o-mini", "deepseek-ai/deepseek-v4-flash", "openrouter/free", "gemini-2.5-flash", "claude-haiku-4-5"]
CLASSIFIER_TIMEOUT = 5  # seconds per attempt


async def classify_intent(
    user_message: str,
    router: LLMRouter,
) -> DispatchResult:
    """Use a cheap/fast LLM call to classify user intent.

    Fallback chain: Gemini Flash → OpenRouter/free → Claude Haiku
    Each attempt has a 5-second timeout for fast failure.
    Keyword fallback only as absolute last resort.
    """
    import asyncio

    template = _PROMPT_PATH.read_text(encoding="utf-8") if _PROMPT_PATH.exists() else ""
    if not template:
        return _keyword_fallback(user_message)

    prompt = template.replace("{user_message}", user_message)
    messages = [{"role": "user", "content": prompt}]

    for model in CLASSIFIER_MODELS:
        try:
            response = await asyncio.wait_for(
                router.call(model=model, messages=messages, max_tokens=100, _skip_fallback=True),
                timeout=CLASSIFIER_TIMEOUT,
            )
            text = response.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            if text.startswith("{"):
                data = json.loads(text)
                return DispatchResult(
                    framework=data.get("framework", "single"),
                    skills=data.get("skills", []),
                )
            # LLM responded but not valid JSON — try next model
            logger.warning("classify_intent_bad_json", model=model, response=text[:80])
        except TimeoutError:
            logger.warning("classify_intent_timeout", model=model)
        except Exception as e:
            logger.warning("classify_intent_failed", model=model, error=str(e)[:80])

    # All LLM attempts exhausted — keyword fallback as last resort
    logger.info("classify_intent_keyword_fallback", message=user_message[:50])
    return _keyword_fallback(user_message)


def _keyword_fallback(user_message: str) -> DispatchResult:
    """Fast keyword fallback when LLM classification fails or is skipped."""
    msg = user_message.lower()

    # Multi-agent triggers
    if any(kw in msg for kw in ["全面分析", "詳細分析", "完整分析", "full analysis", "comprehensive"]):
        return DispatchResult(framework="subagent", skills=["stock_analysis", "chip_flow", "earnings_review"])

    if any(kw in msg for kw in ["深度研究", "研究報告", "deep research", "research report"]):
        return DispatchResult(framework="team", skills=["international_stocks", "company_research", "corporate_actions"])

    if any(kw in msg for kw in ["比較", "compare", "vs", "對比", "versus"]):
        return DispatchResult(framework="single", skills=["compare_stocks"])

    # Market overview
    market_kw = ["大盤", "市場總覽", "market overview", "盤勢", "市場概況", "market today", "index"]
    if any(kw in msg for kw in market_kw):
        return DispatchResult(framework="single", skills=["market_briefing"])

    # Single-skill triggers
    if any(kw in msg for kw in ["集保", "股權分散", "持股分布", "tdcc", "shareholding distribution", "ownership"]):
        return DispatchResult(framework="single", skills=["shareholding_analysis"])
    if any(kw in msg for kw in ["法人", "外資", "籌碼", "融資", "融券", "institutional", "foreign investors", "margin trading"]):
        return DispatchResult(framework="single", skills=["chip_flow"])
    if any(kw in msg for kw in ["營收", "財報", "EPS", "revenue", "earnings", "financial statement", "profit"]):
        return DispatchResult(framework="single", skills=["earnings_review"])
    if any(kw in msg for kw in ["重大訊息", "庫藏股", "法說會", "announcement", "buyback", "conference"]):
        return DispatchResult(framework="single", skills=["corporate_actions"])
    if any(kw in msg for kw in ["排行", "除權息", "抽籤", "紀念品", "ranking", "dividend calendar", "ipo lottery"]):
        return DispatchResult(framework="single", skills=["market_movers"])
    if any(kw in msg for kw in ["供應鏈", "ESG", "概念股", "ETF", "supply chain", "theme"]):
        return DispatchResult(framework="single", skills=["company_research"])
    if any(kw in msg for kw in ["美股", "國際", "sector", "us stock", "nasdaq", "s&p"]):
        return DispatchResult(framework="single", skills=["international_stocks"])
    if any(kw in msg for kw in ["選股", "篩選", "screener", "screen", "filter stocks"]):
        return DispatchResult(framework="single", skills=["screener"])
    if any(kw in msg for kw in ["提醒", "通知", "alert", "notify", "remind"]):
        return DispatchResult(framework="single", skills=["alert_setup"])
    if any(kw in msg for kw in ["處置", "警示", "注意股", "disposal", "warning", "risk"]):
        return DispatchResult(framework="single", skills=["anti_fraud"])
    if any(kw in msg for kw in ["分析", "analyze", "看法", "怎麼看", "analysis", "outlook"]):
        return DispatchResult(framework="single", skills=["stock_analysis"])
    if any(kw in msg for kw in ["股價", "價格", "多少錢", "收盤", "price", "quote", "how much"]):
        return DispatchResult(framework="single", skills=["stock_analysis"])

    # No match — greeting, off-topic, or general chat
    return DispatchResult(framework="none", skills=[])


def build_subagent_tasks(
    skills: list[str],
    user_query: str,
    skill_registry: SkillRegistry,
    stock_id: str | None = None,
) -> list[SubagentTask]:
    """Build SubagentTask list from skill names — each skill becomes one subagent."""
    context = user_query
    if stock_id:
        context = f"Stock: {stock_id}\nQuery: {user_query}"

    tasks = []
    for skill_name in skills:
        body = skill_registry.load_body(skill_name)
        if body:
            tasks.append(SubagentTask(
                role=skill_name,
                prompt=body.effective_instructions() or f"You are a {skill_name} analyst.",
                tools=body.tools or [],
                user_context=context,
            ))
    return tasks


def build_team_tasks(
    skills: list[str],
    user_query: str,
    skill_registry: SkillRegistry,
    stock_id: str | None = None,
) -> tuple[list[Teammate], list[TeamTask]]:
    """Build teammates + tasks from skill names for AgentTeam."""
    from app.agent.multi.team import Teammate, TeamTask

    context = user_query
    if stock_id:
        context = f"Stock: {stock_id}\nQuery: {user_query}"

    teammates: list[Teammate] = []
    tasks: list[TeamTask] = []
    for skill_name in skills:
        body = skill_registry.load_body(skill_name)
        if body:
            teammates.append(Teammate(
                name=skill_name,
                role=skill_name,
                prompt=body.effective_instructions() or f"You are a {skill_name} analyst.",
                tools=body.tools or [],
            ))
            tasks.append(TeamTask(
                title=f"{skill_name} analysis",
                description=context,
                assigned_to=skill_name,
            ))
    return teammates, tasks


# --- Legacy compatibility (for existing tests) ---

@dataclass
class Strategy:
    name: str
    description: str
    roles: list[str]


STOCK_ANALYSIS = Strategy("stock_analysis", "Comprehensive single-stock analysis", ["stock_analysis", "chip_flow", "earnings_review"])
MARKET_OVERVIEW = Strategy("market_overview", "Broad market overview", ["market_briefing", "chip_flow", "market_movers"])
COMPARISON = Strategy("comparison", "Compare stocks", ["compare_stocks"])
DEEP_RESEARCH = Strategy("deep_research", "Multi-source deep research", ["international_stocks", "company_research", "corporate_actions"])


def detect_strategy(user_message: str) -> Strategy | None:
    """Legacy keyword-based strategy detection — used by tests and fallback."""
    result = _keyword_fallback(user_message)
    if result.framework in ("subagent", "team"):
        strategy_map = {
            "subagent": {
                frozenset(["stock_analysis", "chip_flow", "earnings_review"]): STOCK_ANALYSIS,
                frozenset(["market_briefing", "chip_flow", "market_movers"]): MARKET_OVERVIEW,
            },
            "team": {
                frozenset(["international_stocks", "company_research", "corporate_actions"]): DEEP_RESEARCH,
            },
        }
        skill_set = frozenset(result.skills)
        for pattern, strategy in strategy_map.get(result.framework, {}).items():
            if skill_set == pattern:
                return strategy
        # Return generic strategy for non-standard skill combos
        if result.framework == "subagent":
            return Strategy("dynamic_subagent", "Dynamic parallel analysis", result.skills)
        return Strategy("dynamic_team", "Dynamic collaborative research", result.skills)
    return None


def build_tasks(strategy: Strategy, user_query: str, stock_id: str | None = None) -> list[SubagentTask]:
    """Legacy: build tasks from strategy roles (uses skill instructions if available)."""
    from app.agent.skills.registry import SkillRegistry
    sr = SkillRegistry()
    return build_subagent_tasks(strategy.roles, user_query, sr, stock_id)


def build_team(strategy: Strategy, user_query: str, stock_id: str | None = None) -> tuple[list[Teammate], list[TeamTask]]:
    """Legacy: build team from strategy roles."""
    from app.agent.skills.registry import SkillRegistry
    sr = SkillRegistry()
    return build_team_tasks(strategy.roles, user_query, sr, stock_id)
