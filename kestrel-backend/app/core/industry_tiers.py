"""Sub-industry → supply-chain tier (upstream/midstream/downstream) heuristic.

Curated `tier_classification` rows in DuckDB are authoritative and win when present
(only ~8 of 48 themes are curated). For every other theme this keyword fallback
classifies a sub_industry name so all themes still render up/mid/down lanes.

Kept as a Python module (matching `core/sector_names.py`, the analogous sector-id
→ name lookup) rather than a JSON asset: the project deliberately moved static data
out of `data/*.json` into DuckDB/code, and a module stays type-checked and importable.
Tune the keyword lists here.
"""

# Checked downstream → upstream → midstream so the most specific end-market
# keywords win; an unmatched sub_industry defaults to midstream.
TIER_KEYWORDS: list[tuple[str, list[str]]] = [
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
    for tier, kws in TIER_KEYWORDS:
        if any(kw in s for kw in kws):
            return tier
    return "midstream"
