"""Agent thinking-process live test — verifies the live reasoning/tool timeline
(bug #2: "thinking process should stream in real-time like Claude Code web").

Drives AgentService.process_stream() per model with db_session=None (memory off) and
captures the ORDERED event stream — every thinking / tool_start / tool_done / text /
status event — so we can prove, per model, whether:
  1. reasoning tokens actually stream (thinking events > 0), and
  2. events arrive INCREMENTALLY (interleaved), not in one end-of-turn burst.

We record the wall-clock offset of each event; if thinking/tool/text events are spread
across the turn (not clustered at the end) the timeline is genuinely real-time.

Writes one markdown report per model to docs/agent-test-reports/thinking_<model>.md.

Usage:
    python -m scripts.agent_thinking_test                       # default model set
    python -m scripts.agent_thinking_test --models claude-opus-4-8 gemini-3.5-flash
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agent.core import AgentService
from app.agent.router import LLMRouter
from app.agent.tools.registry import ToolRegistry
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_registry() -> ToolRegistry:
    """A small but REAL tool set so the agent actually calls a tool (exercising the
    live tool_start → tool_done timeline), without standing up the full 60-tool app."""
    from app.agent.tools.twse_tools import GetRealtimeQuoteTool
    from app.agent.tools.yfinance_tools import GetStockHistoryTool

    reg = ToolRegistry()
    reg.register_many([GetRealtimeQuoteTool(), GetStockHistoryTool()])
    return reg

OUT_DIR = Path(__file__).parent.parent.parent / "docs" / "agent-test-reports"

# A query that should induce both reasoning and at least one tool call (real data).
QUERY = "台積電 (2330) 現在的技術面如何？請查最新股價後再回答。"

# Reasoning-capable / representative models. Kept small to bound API cost.
DEFAULT_MODELS = [
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "deepseek-ai/deepseek-v4-pro",
    "gemini-3.1-pro-preview",
]


async def run_one(model: str, settings: Settings) -> dict[str, Any]:
    """Drive one turn and capture the ordered event timeline."""
    router = LLMRouter(settings)
    service = AgentService(settings=settings, router=router, tool_registry=_build_registry())

    events: list[dict[str, Any]] = []
    t0 = time.monotonic()
    thinking_chars = 0
    text_chars = 0

    try:
        async for ev in service.process_stream(
            user_message=QUERY,
            user_id="thinking-test",
            session_id=None,
            db_session=None,  # memory/DB off — isolate the loop + streaming layer
            model=model,
        ):
            offset_ms = int((time.monotonic() - t0) * 1000)
            etype = getattr(ev, "type", ev.__class__.__name__)
            rec: dict[str, Any] = {"t": offset_ms, "type": etype}
            content = getattr(ev, "content", None)
            delta = getattr(ev, "delta", None)
            if etype in ("thinking", "ThinkingEvent") and content:
                thinking_chars += len(content)
            if delta:
                text_chars += len(delta)
            # Tool-process fields (Hermes-CLI style: name → summary → duration), so the
            # report proves the tool timeline streams live (start early, done later).
            tool_name = getattr(ev, "display_name", None)
            if tool_name:
                rec["tool"] = tool_name
            summary = getattr(ev, "summary", None)
            if summary:
                rec["summary"] = summary
            duration = getattr(ev, "duration_ms", None)
            if duration:
                rec["duration_ms"] = duration
            status = getattr(ev, "status", None)
            if status:
                rec["status"] = status
            events.append(rec)
    except Exception as e:  # noqa: BLE001
        return {"model": model, "error": str(e)[:300], "events": events}

    # Aggregate the timeline into per-type spans (first/last offset, count).
    spans: dict[str, dict[str, int]] = {}
    for rec in events:
        s = spans.setdefault(rec["type"], {"count": 0, "first": rec["t"], "last": rec["t"]})
        s["count"] += 1
        s["last"] = rec["t"]

    return {
        "model": model,
        "events": events,
        "spans": spans,
        "thinking_chars": thinking_chars,
        "text_chars": text_chars,
        "total_ms": events[-1]["t"] if events else 0,
    }


def _verdict(r: dict[str, Any]) -> dict[str, Any]:
    """Structural checks: did reasoning stream, and was it incremental?"""
    if r.get("error"):
        return {"streamed_thinking": False, "incremental": False, "used_tools": False}
    spans = r.get("spans", {})
    thinking_events = spans.get("thinking", {}).get("count", 0) + spans.get("ThinkingEvent", {}).get("count", 0)
    tool_start = spans.get("tool_start", spans.get("ToolStartEvent", {}))
    tool_done = spans.get("tool_done", spans.get("ToolDoneEvent", {}))
    tool_events = tool_start.get("count", 0)
    # Incremental text = text events span > 500ms between first and last (not a burst).
    text_span = spans.get("text", spans.get("TextEvent", {}))
    incremental = bool(text_span) and (text_span.get("last", 0) - text_span.get("first", 0) > 500)
    # Live tool process = a tool_start fires meaningfully BEFORE its tool_done (the
    # "preparing… → done Xs" progression the user wants), i.e. the gap is observable.
    tool_live = bool(tool_start) and bool(tool_done) and (tool_done.get("last", 0) - tool_start.get("first", 0) > 200)
    return {
        "streamed_thinking": thinking_events > 0,
        "thinking_events": thinking_events,
        "incremental_text": incremental,
        "used_tools": tool_events > 0,
        "tool_process_live": tool_live,
    }


def _report_md(r: dict[str, Any]) -> str:
    v = _verdict(r)
    lines = [
        "# Thinking-process live test",
        "",
        f"- Model: `{r['model']}`",
        f"- Query: {QUERY}",
        "",
        "## Verdict",
        "",
        f"- **Streamed reasoning tokens:** {'✅ yes' if v['streamed_thinking'] else '❌ no'} "
        f"({v.get('thinking_events', 0)} thinking events)",
        f"- **Incremental text stream:** {'✅ yes' if v.get('incremental_text') else '❌ no (burst)'}",
        f"- **Called a tool (real data):** {'✅ yes' if v.get('used_tools') else '❌ no'}",
        f"- **Live tool process (start→done gap):** {'✅ yes' if v.get('tool_process_live') else '❌ no'}",
    ]
    if r.get("error"):
        lines += ["", f"> ⚠️ ERROR: {r['error']}"]
        return "\n".join(lines) + "\n"
    lines += [
        f"- Reasoning chars: {r['thinking_chars']} · Answer chars: {r['text_chars']} · "
        f"Turn: {r['total_ms']}ms",
        "",
        "## Event timeline (offset ms → type)",
        "",
        "| t(ms) | event | detail |",
        "|------:|-------|--------|",
    ]
    # Collapse consecutive text/thinking deltas for readability.
    prev = None
    run_start = 0
    run_n = 0
    collapsed: list[dict[str, Any]] = []
    for e in r["events"]:
        if e["type"] in ("text", "thinking", "TextEvent", "ThinkingEvent"):
            if prev == e["type"]:
                run_n += 1
                continue
            if prev:
                collapsed.append({"t": run_start, "type": prev, "detail": f"×{run_n} deltas"})
            prev = e["type"]
            run_start = e["t"]
            run_n = 1
        else:
            if prev:
                collapsed.append({"t": run_start, "type": prev, "detail": f"×{run_n} deltas"})
                prev = None
            detail = e.get("tool") or e.get("status") or ""
            if e.get("summary"):
                detail = f"{detail} — {e['summary']}".strip(" —")
            if e.get("duration_ms"):
                detail = f"{detail} ({e['duration_ms']}ms)".strip()
            collapsed.append({"t": e["t"], "type": e["type"], "detail": detail})
    if prev:
        collapsed.append({"t": run_start, "type": prev, "detail": f"×{run_n} deltas"})
    for c in collapsed:
        lines.append(f"| {c['t']} | {c['type']} | {c['detail']} |")
    return "\n".join(lines) + "\n"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=DEFAULT_MODELS)
    args = parser.parse_args()

    settings = Settings()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for model in args.models:
        label = model.replace("/", "_")
        logger.info("thinking_test_start", model=model)
        r = await run_one(model, settings)
        report = _report_md(r)
        out = OUT_DIR / f"thinking_{label}.md"
        out.write_text(report, encoding="utf-8")
        v = _verdict(r)
        print(f"\n{'=' * 60}\nMODEL: {model}  →  {out}")
        print("verdict:", v)
        if r.get("error"):
            print("ERROR:", r["error"])
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
