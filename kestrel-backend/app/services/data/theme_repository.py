"""DuckDB-backed repository for theme / membership / tier / supply-chain data.

This is the single source of truth that replaced the old data/*.json files.

Data provenance (most authoritative first — matches how the data is sourced):
- themes + memberships: FinMind TaiwanStockIndustryChain (structured, authoritative)
- tier: rule mapping from sub_industry → tier (curated `tier_classification` rows)
- supply_chain_edges: LLM extraction (no structured TW supply-chain-edge dataset
  exists), so these carry a `confidence` and `source` for transparency.

All reads filter soft-deleted rows (removed_at IS NULL). Writes are idempotent
(INSERT OR REPLACE) and append to `theme_change_log` for audit/rollback.
"""

from typing import Any
from uuid import uuid4

from app.db.duckdb.engine import DuckDBEngine, get_duckdb

# Keyword → tier heuristic for sub_industries with no curated tier_classification
# row (only 8 of 48 themes are curated). Checked downstream→upstream so the most
# specific end-market keywords win; unmatched defaults to midstream.
_TIER_KEYWORDS: list[tuple[str, list[str]]] = [
    ("downstream", ["通路", "零售", "品牌", "終端", "應用", "系統整合", "系統", "服務",
                     "電商", "銷售", "代理商、經銷商", "經銷", "餐飲", "百貨", "醫院",
                     "整車", "整機", "成品", "客戶"]),
    ("upstream", ["製造", "材料", "原料", "晶圓", "設備", "零組件", "化學", "化學品",
                  "礦", "基板", "導線架", "光罩", "矽智財", "晶圓製造", "面板", "電池芯",
                  "封測", "封裝", "代工", "鑄造", "上游"]),
    ("midstream", ["設計", "模組", "代理", "加工", "中游", "IC設計", "IP", "組裝",
                   "貿易商", "經銷商"]),
]


def classify_tier(sub_industry: str) -> str:
    """Best-effort upstream/midstream/downstream from a sub_industry name."""
    s = sub_industry or ""
    for tier, kws in _TIER_KEYWORDS:
        if any(kw in s for kw in kws):
            return tier
    return "midstream"


class ThemeRepository:
    def __init__(self, db: DuckDBEngine | None = None) -> None:
        self._db = db or get_duckdb()

    # ---- async read API (used by request handlers) ----

    async def list_themes(self, include_proposed: bool = False) -> list[dict[str, Any]]:
        status_filter = "" if include_proposed else "WHERE t.status = 'active'"
        # Single query: aggregate distinct sub_industries per theme inline
        # (DuckDB list(DISTINCT ...)) so we avoid the previous N+1 — one extra
        # query per theme — which scaled linearly with theme count.
        rows = await self._db.aquery(f"""
            SELECT t.theme_id, t.name_zh, t.name_en, t.status, t.source,
                   COUNT(m.stock_id) FILTER (WHERE m.removed_at IS NULL) AS stock_count,
                   list(DISTINCT m.sub_industry) FILTER (
                       WHERE m.removed_at IS NULL AND m.sub_industry <> ''
                   ) AS sub_industries
            FROM themes t
            LEFT JOIN theme_memberships m ON m.theme_id = t.theme_id
            {status_filter}
            GROUP BY t.theme_id, t.name_zh, t.name_en, t.status, t.source
            ORDER BY stock_count DESC
        """)
        return [
            {
                "id": r[0],
                "name_zh": r[1],
                "name_en": r[2] or "",
                "stock_count": r[5],
                "sub_industries": list(r[6]) if r[6] else [],
            }
            for r in rows
        ]

    def list_theme_names_sync(self) -> list[str]:
        """All active theme ids/names (sync — used by cron discovery for dedup)."""
        rows = self._db.read_connection().execute(
            "SELECT theme_id FROM themes WHERE status IN ('active', 'proposed')"
        ).fetchall()
        return [r[0] for r in rows]

    async def search_themes(self, query: str) -> list[dict[str, Any]]:
        q = f"%{query.lower()}%"
        rows = await self._db.aquery("""
            SELECT t.theme_id, t.name_zh, t.name_en,
                   COUNT(m.stock_id) FILTER (WHERE m.removed_at IS NULL) AS stock_count
            FROM themes t
            LEFT JOIN theme_memberships m ON m.theme_id = t.theme_id
            WHERE t.status = 'active'
              AND (LOWER(t.name_zh) LIKE ? OR LOWER(t.theme_id) LIKE ? OR LOWER(t.name_en) LIKE ?)
            GROUP BY t.theme_id, t.name_zh, t.name_en
            ORDER BY stock_count DESC
        """, [q, q, q])
        return [
            {"id": r[0], "name_zh": r[1], "name_en": r[2] or "", "stock_count": r[3], "sub_industries": []}
            for r in rows
        ]

    async def get_theme_stocks(self, theme_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = await self._db.aquery("""
            SELECT stock_id, theme_id, sub_industry, source
            FROM theme_memberships
            WHERE theme_id = ? AND removed_at IS NULL
            ORDER BY stock_id
            LIMIT ?
        """, [theme_id, limit])
        return [
            {"stock_id": r[0], "theme_id": r[1], "sub_industry": r[2], "source": r[3]}
            for r in rows
        ]

    async def get_theme_tiers(self, theme_id: str, per_tier: int = 20) -> dict[str, Any]:
        """Group a theme's stocks by tier using the sub_industry → tier mapping."""
        tier_rows = await self._db.aquery(
            "SELECT sub_industry, tier FROM tier_classification WHERE theme_id = ?",
            [theme_id],
        )
        tier_map = {r[0]: r[1] for r in tier_rows}
        members = await self.get_theme_stocks(theme_id, limit=500)

        buckets: dict[str, list[dict[str, Any]]] = {"upstream": [], "midstream": [], "downstream": []}
        for m in members:
            sub = m.get("sub_industry", "")
            # Curated mapping wins; keyword heuristic covers the ~40 themes with no
            # tier_classification rows (so every theme gets real up/mid/down lanes).
            tier = tier_map.get(sub) or classify_tier(sub)
            buckets.setdefault(tier, buckets["midstream"]).append(m)

        return {
            "data": {k: v[:per_tier] for k, v in buckets.items()},
            "theme_id": theme_id,
            "tier_defined": bool(tier_map),
        }

    async def distinct_theme_sub_industries(self) -> list[tuple[str, str]]:
        """Every (theme_id, sub_industry) pair across active memberships — used by
        the tier-seed cron to backfill tier classification for all themes."""
        rows = await self._db.aquery("""
            SELECT DISTINCT theme_id, sub_industry
            FROM theme_memberships
            WHERE removed_at IS NULL AND sub_industry <> ''
        """)
        return [(r[0], r[1]) for r in rows]

    async def get_theme_structure(self, theme_id: str, limit: int = 200) -> dict[str, Any]:
        """Enriched member list powering the industry-structure modal (role
        grouping + comparison).

        One pass joins memberships -> tier (curated mapping, default midstream) ->
        latest-day trading value (for a relevance rating, since membership.confidence
        is effectively constant and most themes have no tier mapping) -> supply-chain
        edge degree. Relevance high/medium/low is by trading-value rank WITHIN the
        theme: the most-traded names are the most representative. Always populated.
        """
        members = await self.get_theme_stocks(theme_id, limit=limit)
        if not members:
            return {"theme_id": theme_id, "members": [], "tier_defined": False}

        tier_rows = await self._db.aquery(
            "SELECT sub_industry, tier FROM tier_classification WHERE theme_id = ?",
            [theme_id],
        )
        tier_map = {r[0]: r[1] for r in tier_rows}

        ids = [m["stock_id"] for m in members]
        ph = ",".join("?" * len(ids))

        # Latest-day close/spread/trading-value per member (DuckDB price_daily).
        price_rows = await self._db.aquery(f"""
            SELECT stock_id, close, spread, amount FROM price_daily p
            WHERE stock_id IN ({ph})
              AND date = (SELECT MAX(date) FROM price_daily WHERE stock_id = p.stock_id)
        """, ids)
        price_map = {r[0]: {"close": r[1], "spread": r[2], "amount": r[3] or 0} for r in price_rows}

        # Edge degree per member (real supply-chain relationships).
        edge_rows = await self._db.aquery(f"""
            SELECT stock_id, type, n FROM (
                SELECT from_id AS stock_id, type, COUNT(*) AS n FROM supply_chain_edges
                WHERE removed_at IS NULL AND from_id IN ({ph}) GROUP BY from_id, type
                UNION ALL
                SELECT to_id AS stock_id, type, COUNT(*) AS n FROM supply_chain_edges
                WHERE removed_at IS NULL AND to_id IN ({ph}) GROUP BY to_id, type
            )
        """, ids + ids)
        edge_map: dict[str, dict[str, int]] = {}
        for sid, etype, n in edge_rows:
            edge_map.setdefault(sid, {})
            edge_map[sid][etype] = edge_map[sid].get(etype, 0) + int(n)

        # Relevance rating: rank members by trading value, split into high/med/low thirds.
        ranked = sorted(members, key=lambda m: price_map.get(m["stock_id"], {}).get("amount", 0), reverse=True)
        n = len(ranked)
        relevance: dict[str, str] = {}
        for i, m in enumerate(ranked):
            amt = price_map.get(m["stock_id"], {}).get("amount", 0)
            if amt <= 0:
                relevance[m["stock_id"]] = "low"
            elif i < n / 3:
                relevance[m["stock_id"]] = "high"
            elif i < 2 * n / 3:
                relevance[m["stock_id"]] = "medium"
            else:
                relevance[m["stock_id"]] = "low"

        out_members: list[dict[str, Any]] = []
        for m in members:
            sid = m["stock_id"]
            sub = m.get("sub_industry", "")
            pr = price_map.get(sid, {})
            # Curated tier wins; otherwise classify the sub_industry by keyword so
            # all 48 themes get up/mid/down lanes (only 8 are curated).
            tier = tier_map.get(sub) or classify_tier(sub)
            out_members.append({
                "stock_id": sid,
                "sub_industry": sub,
                "tier": tier,
                "relevance": relevance.get(sid, "low"),
                "edges": edge_map.get(sid, {}),
                "close": pr.get("close"),
                "spread": pr.get("spread"),
            })

        return {"theme_id": theme_id, "members": out_members, "tier_defined": bool(tier_map)}

    async def get_stock_edges(self, stock_id: str) -> list[dict[str, Any]]:
        rows = await self._db.aquery("""
            SELECT from_id, from_name, to_id, to_name, type, confidence, revenue_pct
            FROM supply_chain_edges
            WHERE (from_id = ? OR to_id = ?) AND removed_at IS NULL
        """, [stock_id, stock_id])
        return [self._edge_dict(r) for r in rows]

    async def get_theme_graph(self, theme_id: str) -> dict[str, Any]:
        member_rows = await self._db.aquery(
            "SELECT stock_id FROM theme_memberships WHERE theme_id = ? AND removed_at IS NULL",
            [theme_id],
        )
        stock_ids = {r[0] for r in member_rows}
        if not stock_ids:
            return {"nodes": [], "edges": [], "theme_id": theme_id}

        placeholders = ",".join("?" * len(stock_ids))
        ids = list(stock_ids)
        edge_rows = await self._db.aquery(f"""
            SELECT from_id, from_name, to_id, to_name, type, confidence, revenue_pct
            FROM supply_chain_edges
            WHERE removed_at IS NULL AND (from_id IN ({placeholders}) OR to_id IN ({placeholders}))
        """, ids + ids)
        edges = [self._edge_dict(r) for r in edge_rows]

        node_ids: set[str] = set()
        labels: dict[str, str] = {}
        for e in edges:
            node_ids.add(e["from"])
            node_ids.add(e["to"])
            labels.setdefault(e["from"], e.get("from_name") or e["from"])
            labels.setdefault(e["to"], e.get("to_name") or e["to"])

        return {
            "nodes": [{"id": nid, "label": labels.get(nid, nid)} for nid in node_ids],
            "edges": [
                {"id": f"e{i}", "source": e["from"], "target": e["to"], "label": e["type"]}
                for i, e in enumerate(edges)
            ],
            "theme_id": theme_id,
        }

    @staticmethod
    def _edge_dict(r: tuple[Any, ...]) -> dict[str, Any]:
        return {
            "from": r[0], "from_name": r[1], "to": r[2], "to_name": r[3],
            "type": r[4], "confidence": r[5], "revenue_pct": r[6],
        }

    # ---- sync write API (used by seed/discovery cron jobs) ----

    def upsert_theme(self, theme_id: str, name_zh: str, name_en: str = "",
                     status: str = "active", source: str = "finmind_industry_chain") -> None:
        with self._db.write_connection() as conn:
            existing = conn.execute("SELECT 1 FROM themes WHERE theme_id = ?", [theme_id]).fetchone()
            conn.execute("""
                INSERT OR REPLACE INTO themes (theme_id, name_zh, name_en, status, source, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [theme_id, name_zh, name_en, status, source])
            self._log(conn, "theme", theme_id, "update" if existing else "create", source, name_zh)

    def upsert_membership(self, stock_id: str, theme_id: str, sub_industry: str = "",
                          confidence: float = 1.0, source: str = "finmind_industry_chain") -> None:
        with self._db.write_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO theme_memberships
                    (stock_id, theme_id, sub_industry, confidence, source, added_at, removed_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
            """, [stock_id, theme_id, sub_industry, confidence, source])

    def clear_theme_members(self, theme_id: str, source: str) -> int:
        """Soft-delete a theme's memberships from a given source (so a re-seed is a
        fresh snapshot, not an ever-growing union of every past run)."""
        with self._db.write_connection() as conn:
            cur = conn.execute("""
                UPDATE theme_memberships SET removed_at = CURRENT_TIMESTAMP
                WHERE theme_id = ? AND source = ? AND removed_at IS NULL
            """, [theme_id, source])
            return cur.rowcount if hasattr(cur, "rowcount") else 0

    def clear_edges(self, source: str) -> int:
        """Hard-delete supply-chain edges from a given source (so a re-generation
        run is a fresh snapshot). Used by the LLM edge-gen seed ('edge_gen')."""
        with self._db.write_connection() as conn:
            cur = conn.execute("DELETE FROM supply_chain_edges WHERE source = ?", [source])
            return cur.rowcount if hasattr(cur, "rowcount") else 0

    def set_tier(self, theme_id: str, sub_industry: str, tier: str) -> None:
        with self._db.write_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tier_classification (theme_id, sub_industry, tier, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, [theme_id, sub_industry, tier])

    def upsert_edge(self, from_id: str, to_id: str, edge_type: str, from_name: str = "",
                    to_name: str = "", confidence: str = "medium", revenue_pct: float | None = None,
                    source: str = "llm_extraction") -> None:
        with self._db.write_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO supply_chain_edges
                    (from_id, to_id, type, from_name, to_name, confidence, revenue_pct, source, updated_at, removed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, NULL)
            """, [from_id, to_id, edge_type, from_name, to_name, confidence, revenue_pct, source])

    @staticmethod
    def _log(conn: Any, entity: str, entity_id: str, action: str, source: str, detail: str = "") -> None:
        conn.execute("""
            INSERT INTO theme_change_log (id, entity, entity_id, action, detail, source)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [str(uuid4()), entity, entity_id, action, detail[:200], source])
