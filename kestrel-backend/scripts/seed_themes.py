"""Seed theme / membership / tier data into DuckDB from FinMind structured data.

Source of truth for the initial build (no LLM): FinMind TaiwanStockIndustryChain
gives each stock's industry + sub_industry. The curated sub_industry → tier map
(formerly data/tier_classification.json) classifies upstream/midstream/downstream.

Run once to bootstrap, and re-run safely (idempotent upserts) to pick up new
stocks/industries FinMind has added since last run.

Usage: python -m scripts.seed_themes
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.constants import FinMindDataset
from app.core.logging import get_logger
from app.db.duckdb.engine import get_duckdb
from app.providers.finmind.provider import FinMindProvider
from app.services.data.theme_repository import ThemeRepository

logger = get_logger(__name__)

# Curated tier knowledge (sub_industry → tier), retained from the old
# tier_classification.json. This is editorial domain knowledge, not data FinMind
# provides, so we keep it in-repo and seed it into the tier_classification table.
_TIER_SEED_PATH = Path(__file__).parent.parent / "data" / "tier_classification.json"


def _load_tier_seed() -> dict[str, dict[str, list[str]]]:
    if not _TIER_SEED_PATH.exists():
        return {}
    with open(_TIER_SEED_PATH, encoding="utf-8") as f:
        return cast("dict[str, dict[str, list[str]]]", json.load(f))


async def seed_from_industry_chain() -> dict[str, int]:
    """Build themes + memberships from FinMind TaiwanStockIndustryChain."""
    settings = Settings()
    provider = FinMindProvider(settings)
    await provider.initialize()
    try:
        rows = await provider.fetch(FinMindDataset.TAIWAN_STOCK_INDUSTRY_CHAIN)
    finally:
        await provider.close()

    repo = ThemeRepository()
    themes_seen: set[str] = set()
    membership_count = 0

    # Batch all per-row upserts into one transaction (the nested write_connection()
    # blocks inside each upsert_* join this outer txn) — one commit, not thousands.
    with get_duckdb().write_connection():
        for row in rows or []:
            stock_id = row.get("stock_id", "")
            industry = row.get("industry", "")
            sub_industry = row.get("sub_industry", "")
            if not stock_id or not industry:
                continue

            if industry not in themes_seen:
                repo.upsert_theme(theme_id=industry, name_zh=industry, source="finmind_industry_chain")
                themes_seen.add(industry)

            repo.upsert_membership(
                stock_id=stock_id, theme_id=industry, sub_industry=sub_industry,
                source="finmind_industry_chain",
            )
            membership_count += 1

    logger.info("industry_chain_seeded", themes=len(themes_seen), memberships=membership_count)
    return {"themes": len(themes_seen), "memberships": membership_count}


async def seed_tiers() -> int:
    """Seed the sub_industry → tier mapping into tier_classification.

    Two layers: (1) curated editorial JSON (authoritative, ~8 themes), then
    (2) a keyword classifier (core/industry_tiers) backfills EVERY remaining
    (theme, sub_industry) pair so all ~48 themes get up/mid/down lanes — fixing
    the old gap where only curated themes had tiers. Curated rows are written
    last-wins so the heuristic never overrides editorial knowledge.
    """
    from app.core.industry_tiers import classify_tier

    repo = ThemeRepository()
    tier_seed = _load_tier_seed()
    # Read all (theme, sub) pairs BEFORE opening the write txn — acquiring the read
    # lock inside a write_connection() can deadlock.
    pairs = await repo.distinct_theme_sub_industries()

    # Curated (theme, sub) pairs — so we don't overwrite them with the heuristic.
    curated: set[tuple[str, str]] = set()
    count = 0
    with get_duckdb().write_connection():
        # (1) curated editorial mappings (authoritative)
        for theme_id, tiers in tier_seed.items():
            if theme_id.startswith("_"):  # skip _default
                continue
            for tier, subs in tiers.items():
                for sub in subs:
                    repo.set_tier(theme_id=theme_id, sub_industry=sub, tier=tier)
                    curated.add((theme_id, sub))
                    count += 1

        # (2) heuristic backfill for every (theme, sub_industry) not curated
        for theme_id, sub in pairs:
            if not sub or (theme_id, sub) in curated:
                continue
            repo.set_tier(theme_id=theme_id, sub_industry=sub, tier=classify_tier(sub))
            count += 1

    logger.info("tiers_seeded", mappings=count, curated=len(curated))
    return count


_RELATIONSHIPS_SEED_PATH = Path(__file__).parent.parent / "data" / "supply_chain" / "relationships.json"


def seed_supply_chain() -> int:
    """One-time migration of curated supply-chain edges into DuckDB.

    These hand-seeded edges bootstrap the graph; future edges come from the
    LLM extraction cron writing to supply_chain_edges directly.
    """
    if not _RELATIONSHIPS_SEED_PATH.exists():
        return 0
    with open(_RELATIONSHIPS_SEED_PATH, encoding="utf-8") as f:
        rels = json.load(f)
    repo = ThemeRepository()
    count = 0
    with get_duckdb().write_connection():
        for r in rels:
            if not r.get("from") or not r.get("to"):
                continue
            repo.upsert_edge(
                from_id=r["from"], to_id=r["to"], edge_type=r.get("type", "supplies"),
                from_name=r.get("from_name", ""), to_name=r.get("to_name", ""),
                confidence=r.get("confidence", "medium"), revenue_pct=r.get("revenue_pct"),
                source="seed_migration",
            )
            count += 1
    logger.info("supply_chain_seeded", edges=count)
    return count


_CONCEPT_SEED_PATH = Path(__file__).parent.parent / "data" / "concept_themes.json"


# Two RESEARCHERS (DIFFERENT paid models for genuine independence) research each
# theme's TW constituents from web search + our data; a VERIFIER (paid) reconciles.
# Paid models (Sonnet 4.6 / GPT-4o) lead so the pipeline isn't starved by free-tier
# 429s; free models trail as fallback only if a paid call errors.
_RESEARCHER_A = ["claude-sonnet-4-6", "gpt-4o", "deepseek-ai/deepseek-v4-pro"]
_RESEARCHER_B = ["gpt-4o", "claude-sonnet-4-6", "gemini-2.5-flash"]
_VERIFIER = ["claude-sonnet-4-6", "gpt-4o", "claude-haiku-4-5"]

_RESEARCH_PROMPT = """你是專業的台灣股市產業研究員。請依據下列「即時網路搜尋結果」與「我方產業資料」，列出概念主題「{name_zh}（{name_en}）」目前在台股的成分股。

概念範圍：{hint}

=== 即時網路搜尋結果 ===
{web}

=== 我方產業/新聞資料 ===
{local}

規則：
1. 以上述證據為主要依據，不要單憑記憶；證據未支持者請勿列入。
2. 只列實際在台股掛牌、正確 4 碼代號的個股；絕不編造代號。
3. 每檔附細分角色（sub_industry）與一句 reason（引用是哪個證據）。
4. 列出 8-30 檔最具代表性者。

輸出 JSON：{{"stocks":[{{"stock_id":"1234","sub_industry":"細分角色","reason":"依據"}}]}}"""

_RECONCILE_PROMPT = """你是嚴謹的台灣股市產業驗證分析師。兩位研究員各自（基於網路搜尋＋產業資料）提出「{name_zh}（{name_en}）」的候選成分股。

概念範圍：{hint}

兩位都認同（高信心，傾向保留）：
{agreed}

僅一位提出（需你判斷是否屬於此概念供應鏈）：
{disputed}

任務：保留所有「兩位都認同」者；對「僅一位提出」者，依產業常識與其 reason 判斷，保留合理者、剔除明顯誤判者。

輸出 JSON：{{"keep":["1234","5678",...]}}（最終確定保留的全部股票代號）。"""


# Small pacing between fallback retries (paid models lead, so 429s are rare).
_LLM_PACE_SECONDS = 1.0


async def _route_json(router: Any, models: list[str], prompt: str, key: str) -> Any:
    """Call the first working model in `models` (fallback chain) and parse JSON[key].
    Sleeps between fallback attempts so a burst can't trip the rate limit."""
    import json as _json
    messages = [{"role": "user", "content": prompt}]
    for i, model in enumerate(models):
        if i:
            await asyncio.sleep(_LLM_PACE_SECONDS)  # pace fallback retries
        try:
            resp = await router.call(model=model, messages=messages, max_tokens=1400, _skip_fallback=True)
            text = (resp.text or "").strip()
            if text.startswith("```"):
                text = text.strip("`").lstrip("json").strip()
            val = _json.loads(text).get(key)
            if val:
                return val
        except Exception:
            continue
    return None


async def seed_concept_themes() -> int:
    """Seed curated hot concept themes (data/concept_themes.json) via research +
    reconcile: (1) TWO researchers (different models) each list constituents grounded
    in WEB SEARCH + our own industry/news data; (2) a VERIFIER reconciles — keeps
    stocks both found, judges stocks only one found, drops mismatches. Only stock_ids
    in the real FinMind universe survive (no fabricated codes). Replace-per-source →
    reproducible snapshot. confidence: 0.9 if both researchers agreed, else 0.6."""
    settings = Settings()
    if not _CONCEPT_SEED_PATH.exists():
        return 0
    with open(_CONCEPT_SEED_PATH, encoding="utf-8") as f:
        concepts = json.load(f).get("themes", [])

    from app.agent.router import LLMRouter
    from app.agent.tools.web_search import WebSearchTool
    router = LLMRouter(settings)
    web_tool = WebSearchTool()

    repo = ThemeRepository()
    valid_rows = await repo._db.aquery("SELECT DISTINCT stock_id FROM theme_memberships")
    valid_ids = {r[0] for r in valid_rows}
    # id -> existing industry_category (our data), for local grounding.
    name_rows = await repo._db.aquery("SELECT stock_id, list(DISTINCT sub_industry) FROM theme_memberships WHERE removed_at IS NULL GROUP BY stock_id")
    local_industry = {r[0]: ", ".join(x for x in (r[1] or []) if x)[:60] for r in name_rows}

    sem = asyncio.Semaphore(4)

    async def _evidence(name_zh: str, hint: str) -> tuple[str, str]:
        """Gather web-search snippets (primary) + a corroborating slice of our own
        data: universe stocks whose industry/sub_industry already contains a theme
        keyword (so the researchers can cross-reference real listed names)."""
        async with sem:
            try:
                res = await web_tool.execute({"query": f"{name_zh} 概念股 成分股 台股 供應鏈", "num_results": 8})
                web = (res.content or "")[:2500]
            except Exception:
                web = ""
        # Local corroboration: our stocks whose sub_industry shares a CJK keyword
        # with the theme name/hint (cheap substring match over what we already store).
        terms = {ch for ch in (name_zh + hint) if "一" <= ch <= "鿿"}
        hits = [f"{sid}({ind})" for sid, ind in local_industry.items()
                if ind and any(t in ind for t in terms)][:40]
        local = "、".join(hits) if hits else "（我方資料無直接對應，請以網路搜尋為主）"
        return web or "（無搜尋結果）", local

    async def _research(models: list[str], name_zh: str, name_en: str, hint: str, web: str, local: str) -> dict[str, dict[str, str]]:
        prompt = _RESEARCH_PROMPT.format(name_zh=name_zh, name_en=name_en, hint=hint, web=web, local=local)
        async with sem:
            stocks = await _route_json(router, models, prompt, "stocks") or []
        out: dict[str, dict[str, str]] = {}
        for m in stocks:
            sid = str(m.get("stock_id", "")).strip()
            if sid in valid_ids:
                out[sid] = {"sub_industry": m.get("sub_industry", ""), "reason": m.get("reason", "")}
        return out

    async def _pipeline(c: dict[str, str]) -> tuple[str, str, list[dict[str, Any]]] | None:
        name_zh = (c.get("name_zh") or "").strip()
        if not name_zh:
            return None
        name_en, hint = c.get("name_en", ""), c.get("hint", "")

        web, local = await _evidence(name_zh, hint)
        a, b = await asyncio.gather(
            _research(_RESEARCHER_A, name_zh, name_en, hint, web, local),
            _research(_RESEARCHER_B, name_zh, name_en, hint, web, local),
        )
        if not a and not b:
            return None

        agreed = {sid for sid in a if sid in b}
        disputed = (set(a) | set(b)) - agreed

        def _sub(sid: str) -> str:
            return a.get(sid, {}).get("sub_industry") or b.get(sid, {}).get("sub_industry") or ""
        def _reason(sid: str) -> str:
            return a.get(sid, {}).get("reason") or b.get(sid, {}).get("reason") or ""

        # Verifier reconciles: agreed kept by default, disputed judged on evidence.
        keep = set(agreed)
        if disputed:
            agreed_txt = "\n".join(f"- {s} ({_sub(s)})" for s in agreed) or "（無）"
            disputed_txt = "\n".join(f"- {s} ({_sub(s)}) 理由：{_reason(s)}" for s in disputed) or "（無）"
            prompt = _RECONCILE_PROMPT.format(name_zh=name_zh, name_en=name_en, hint=hint, agreed=agreed_txt, disputed=disputed_txt)
            async with sem:
                verdict = await _route_json(router, _VERIFIER, prompt, "keep")
            if verdict is not None:
                vset = {str(s).strip() for s in verdict}
                keep = (agreed | (disputed & vset))  # never drop an agreed stock
            else:
                keep = agreed | disputed  # verifier failed → fail-open to union

        kept = [
            {"stock_id": sid, "sub_industry": _sub(sid), "confidence": 0.9 if sid in agreed else 0.6}
            for sid in keep
        ]
        logger.info("concept_theme_researched", theme=name_zh, a=len(a), b=len(b), agreed=len(agreed), kept=len(kept))
        return (name_zh, name_en, kept) if kept else None

    gathered = await asyncio.gather(*[_pipeline(c) for c in concepts])
    resolved = [r for r in gathered if r is not None]

    count = 0
    with get_duckdb().write_connection():
        for name_zh, name_en, members in resolved:
            repo.upsert_theme(theme_id=name_zh, name_zh=name_zh, name_en=name_en,
                              status="active", source="concept_seed")
            repo.clear_theme_members(name_zh, source="concept_seed")  # replace, not union
            for m in members:
                repo.upsert_membership(stock_id=str(m["stock_id"]), theme_id=name_zh,
                                       sub_industry=str(m["sub_industry"]),
                                       confidence=float(m["confidence"]), source="concept_seed")
                count += 1
            logger.info("concept_theme_seeded", theme=name_zh, members=len(members))
    logger.info("concept_themes_complete", themes=len(resolved), memberships=count)
    return count


_EDGE_PROMPT = """你是台灣股市供應鏈分析師。下列是「{name_zh}（{name_en}）」概念主題的成分股：

{members}

=== 即時網路搜尋結果（供參考） ===
{web}

任務：找出這些「清單內個股之間」的真實產業關係。只在「清單內」的兩檔之間連線，不要連到清單外的公司。
關係類型：supplies（A 供貨給 B）、customer（A 是 B 的客戶）、competes（A 與 B 競爭）。
只列出你有把握的關係（寧缺勿濫）。

輸出 JSON：{{"edges":[{{"from":"1234","to":"5678","type":"supplies"}}]}}"""

_EDGE_TYPES = {"supplies", "customer", "competes"}
_EDGE_MODELS = ["claude-sonnet-4-6", "gpt-4o", "deepseek-ai/deepseek-v4-pro"]


async def seed_supply_chain_edges() -> int:
    """Generate supplier/customer/competitor edges AMONG each theme's member stocks
    (the colored 供應/競合/客戶 lines in 關聯網絡). supply_chain_edges ships nearly
    empty (15 rows) so the graph had only synthesized grey tier-flow; this fills real
    typed relationships via a paid, web-grounded LLM. Edges between MEMBER ids only
    (no fabricated nodes). Replace-per-source ('edge_gen'). Runs after memberships."""
    settings = Settings()
    from app.agent.router import LLMRouter
    from app.agent.tools.web_search import WebSearchTool
    router = LLMRouter(settings)
    web_tool = WebSearchTool()
    repo = ThemeRepository()

    # Themes worth drawing edges for: the curated concept themes + any with members.
    theme_rows = await repo._db.aquery("""
        SELECT theme_id, list(stock_id) FROM theme_memberships
        WHERE removed_at IS NULL AND source = 'concept_seed'
        GROUP BY theme_id HAVING COUNT(*) >= 3
    """)
    sem = asyncio.Semaphore(4)

    async def _gen(theme_id: str, member_ids: list[str]) -> tuple[str, list[dict[str, str]]]:
        members = set(member_ids)
        listing = "、".join(member_ids)
        async with sem:
            try:
                res = await web_tool.execute({"query": f"{theme_id} 供應鏈 上下游 客戶 競爭 台股", "num_results": 6})
                web = (res.content or "")[:2000]
            except Exception:
                web = "（無）"
        prompt = _EDGE_PROMPT.format(name_zh=theme_id, name_en="", members=listing, web=web)
        async with sem:
            raw = await _route_json(router, _EDGE_MODELS, prompt, "edges") or []
        edges = []
        for e in raw:
            f, t, typ = str(e.get("from", "")).strip(), str(e.get("to", "")).strip(), e.get("type", "supplies")
            if f in members and t in members and f != t and typ in _EDGE_TYPES:
                edges.append({"from": f, "to": t, "type": typ})
        return theme_id, edges

    gathered = await asyncio.gather(*[_gen(tid, list(ids)) for tid, ids in theme_rows])

    count = 0
    with get_duckdb().write_connection():
        repo.clear_edges(source="edge_gen")  # replace-per-source, fresh snapshot
        for theme_id, edges in gathered:
            for e in edges:
                repo.upsert_edge(from_id=e["from"], to_id=e["to"], edge_type=e["type"],
                                 source="edge_gen")
                count += 1
            logger.info("theme_edges_seeded", theme=theme_id, edges=len(edges))
    logger.info("supply_chain_edges_generated", total=count)
    return count


async def seed_all() -> dict[str, int]:
    chain = await seed_from_industry_chain()
    concepts = await seed_concept_themes()
    tiers = await seed_tiers()  # after concepts so their sub_industries get tiered too
    edges = seed_supply_chain()
    gen_edges = await seed_supply_chain_edges()  # LLM-generated relationship edges
    result = {**chain, "concept_memberships": concepts, "tier_mappings": tiers,
              "supply_chain_edges": edges, "generated_edges": gen_edges}
    logger.info("theme_seed_complete", **result)
    return result


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    res = asyncio.run(seed_all())
    print(f"Seeded: {res}")
