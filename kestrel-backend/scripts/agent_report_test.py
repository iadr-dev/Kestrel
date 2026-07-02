"""Agent synthesis report test — proves the new structured report (template +
資料來源 + 免責聲明 + citation/boundary discipline) on a FREE and a PAID model, and
saves both for before/after comparison (mirrors the Hermes repo's 02 test folder).

This drives the synthesis step directly with representative analyst section outputs,
so it exercises exactly what changed (synthesis_subagent.md + the skill governance
fields) without standing up the full provider/tool runtime. To test the live
end-to-end path with real data instead, call the running server's /chat/stream with a
`model` override.

Usage:
    python -m scripts.agent_report_test                # free + paid
    python -m scripts.agent_report_test --free-only
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.multi.subagent import SubagentResult, SubagentRunner, SubagentTask
from app.agent.router import LLMRouter
from app.agent.tools.registry import ToolRegistry
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

FREE_MODEL = "chatanywhere/gpt-4o-mini"
PAID_MODEL = "claude-sonnet-4-6"
OUT_DIR = Path(__file__).parent.parent.parent / "docs" / "agent-test-reports"

QUERY = "全面分析台積電 (2330)"

# Representative analyst outputs (what the stock_analysis / chip_flow / earnings_review
# subagents would return). Dated so we can verify the synthesis preserves source dates.
SECTIONS = [
    (
        "stock_analysis",
        "📈 技術面 (資料日期 2026-06-30): 收盤 1085，站上 MA5/MA20/MA60，多頭排列。"
        "KD 81 偏高、MACD 紅柱續增、RSI 68。短線偏多但接近超買。支撐 1050，壓力 1120。",
    ),
    (
        "chip_flow",
        "🏦 籌碼面 (資料日期 2026-06-30): 外資近5日買超 1.2萬張、近20日買超 4.8萬張；"
        "投信小幅買超；自營商中性。融資餘額微降，籌碼穩定，主力持續偏多。",
    ),
    (
        "earnings_review",
        "💰 基本面: 5月營收 2600億 (YoY +38%, MoM +5%, 資料月份 2026-05)；"
        "2026 Q1 EPS 13.9、毛利率 58%、淨利率 42% (期別 2026Q1)。本益比約 22 倍，高於5年均值。",
    ),
]


async def run_one(model: str, settings: Settings) -> str:
    router = LLMRouter(settings)
    tasks = [SubagentTask(role=role, prompt="", tools=[], user_context=QUERY, result=text) for role, text in SECTIONS]
    result = SubagentResult(tasks=tasks, total_duration_ms=0, success_count=len(tasks), error_count=0)

    # Force the synthesis onto the target model for a clean per-model comparison.
    orig_chat = router.chat

    async def forced_chat(messages, tools=None, max_tokens=4096, model=None):  # type: ignore[no-untyped-def]
        return await orig_chat(messages, tools=tools, max_tokens=max_tokens, model=forced_chat.target)  # type: ignore[attr-defined]

    forced_chat.target = model  # type: ignore[attr-defined]
    router.chat = forced_chat  # type: ignore[method-assign]

    runner = SubagentRunner(router=router, tool_registry=ToolRegistry())
    return await runner.synthesize(QUERY, result)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--free-only", action="store_true")
    args = parser.parse_args()

    settings = Settings()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    models = [FREE_MODEL] if args.free_only else [FREE_MODEL, PAID_MODEL]

    for model in models:
        label = model.replace("/", "_")
        logger.info("agent_report_test_start", model=model)
        try:
            report = await run_one(model, settings)
        except Exception as e:
            report = f"# ERROR ({model})\n\n{e}"
            logger.error("agent_report_test_failed", model=model, error=str(e)[:200])
        out = OUT_DIR / f"synthesis_{label}.md"
        out.write_text(
            f"# Synthesis report test\n\n- Model: `{model}`\n- Query: {QUERY}\n\n---\n\n{report}\n",
            encoding="utf-8",
        )
        logger.info("agent_report_test_saved", path=str(out), chars=len(report))
        # quick structural assertions
        checks = {
            "disclaimer": "不構成任何投資建議" in report or "免責聲明" in report,
            "sources": "資料來源" in report or "來源" in report,
            "dated_figure": "2026-0" in report,
            "complete": report.rstrip().endswith("承擔風險。"),
        }
        print(f"\n{'=' * 60}\nMODEL: {model}  →  {out}")
        print("structure checks:", checks)
        print(f"{'=' * 60}\n{report}\n")


if __name__ == "__main__":
    asyncio.run(main())
