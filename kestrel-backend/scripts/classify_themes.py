"""Theme classification — maps stocks to investment themes + discovers new themes from news.

Two modes:
1. Base classification: Uses TaiwanStockIndustryChain from FinMind (static TWSE categories)
2. Dynamic discovery: LLM analyzes recent news/market trends to propose new themes

Run weekly (Sunday) via APScheduler to keep themes current.
Usage: python -m scripts.classify_themes [--discover]
"""

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.constants import FinMindDataset
from app.core.logging import get_logger
from app.providers.finmind.provider import FinMindProvider

logger = get_logger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
THEMES_FILE = DATA_DIR / "themes.json"
MEMBERSHIPS_FILE = DATA_DIR / "theme_memberships.json"

THEME_DISCOVERY_PROMPT = """你是專業的台灣股市產業分析師。根據以下近期市場資料，分析是否有新的投資主題正在形成。

現有主題列表（{theme_count} 個）：
{existing_themes}

近期市場熱門股票（成交量前30名近5日漲幅）：
{hot_stocks}

請分析：
1. 是否有「尚未在現有主題列表中」的新投資主題正在形成？
2. 新主題必須至少有5檔以上相關股票
3. 不要重複現有主題

輸出 JSON 格式：
{{
  "new_themes": [
    {{
      "id": "主題名稱（繁體中文）",
      "name_zh": "主題名稱",
      "name_en": "English name",
      "reason": "為什麼這是一個新興投資主題",
      "related_stocks": ["stock_id_1", "stock_id_2", ...]
    }}
  ],
  "reclassifications": [
    {{
      "stock_id": "1234",
      "add_theme": "新主題名稱",
      "reason": "為什麼這檔股票應歸入此主題"
    }}
  ]
}}

規則：
- 最多提出3個新主題
- 每個新主題至少5檔股票
- 如果沒有明顯新主題，回傳空陣列
- 不要編造股票代碼
"""


def load_themes() -> list[dict]:
    if THEMES_FILE.exists():
        with open(THEMES_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def load_memberships() -> list[dict]:
    if MEMBERSHIPS_FILE.exists():
        with open(MEMBERSHIPS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


async def fetch_industry_chain(provider: FinMindProvider) -> list[dict]:
    """Fetch TaiwanStockIndustryChain from FinMind."""
    data = await provider.fetch(FinMindDataset.TAIWAN_STOCK_INDUSTRY_CHAIN)
    logger.info("industry_chain_fetched", count=len(data or []))
    return data or []


async def base_classification(provider: FinMindProvider) -> list[dict]:
    """Base classification from FinMind industry chain data."""
    industry_data = await fetch_industry_chain(provider)

    classifications = []
    for row in industry_data:
        stock_id = row.get("stock_id", "")
        industry = row.get("industry", "")
        sub_industry = row.get("sub_industry", "")

        if stock_id and industry:
            classifications.append({
                "stock_id": stock_id,
                "theme_id": industry,
                "sub_industry": sub_industry,
                "source": "finmind_industry_chain",
            })

    # Update themes.json from unique industries
    theme_map: dict[str, dict] = {}
    for c in classifications:
        tid = c["theme_id"]
        if tid not in theme_map:
            theme_map[tid] = {"id": tid, "name_zh": tid, "name_en": "", "stock_count": 0, "sub_industries": []}
        theme_map[tid]["stock_count"] += 1
        sub = c.get("sub_industry", "")
        if sub and sub not in theme_map[tid]["sub_industries"]:
            theme_map[tid]["sub_industries"].append(sub)

    themes = list(theme_map.values())
    with open(THEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(themes, f, ensure_ascii=False, indent=2)

    with open(MEMBERSHIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(classifications, f, ensure_ascii=False, indent=2)

    logger.info("base_classification_complete", themes=len(themes), mappings=len(classifications))
    return classifications


async def discover_new_themes(provider: FinMindProvider, settings: Settings) -> list[dict]:
    """Use LLM to discover emerging investment themes from market data."""
    from app.db.duckdb.engine import get_duckdb

    db = get_duckdb()
    cursor = db.read_connection()

    # Get hot stocks (top 30 by volume with price change)
    hot_stocks_rows = cursor.execute("""
        WITH recent AS (
            SELECT stock_id,
                   FIRST(close) OVER (PARTITION BY stock_id ORDER BY date) as first_close,
                   LAST(close) OVER (PARTITION BY stock_id ORDER BY date) as last_close,
                   SUM(volume) as total_vol
            FROM price_daily
            WHERE date >= CURRENT_DATE - INTERVAL '5 days'
            GROUP BY stock_id, close, date
        )
        SELECT stock_id,
               (MAX(last_close) - MIN(first_close)) / NULLIF(MIN(first_close), 0) * 100 as change_pct,
               SUM(total_vol) as vol
        FROM recent
        GROUP BY stock_id
        ORDER BY vol DESC
        LIMIT 30
    """).fetchall()

    hot_stocks_text = "\n".join([
        f"  {r[0]}: {r[1]:.1f}% (vol: {r[2]:,.0f})" for r in hot_stocks_rows if r[1] is not None
    ])

    existing_themes = load_themes()
    existing_names = ", ".join([t["name_zh"] for t in existing_themes[:30]])

    prompt = THEME_DISCOVERY_PROMPT.format(
        theme_count=len(existing_themes),
        existing_themes=existing_names,
        hot_stocks=hot_stocks_text or "（無近期交易資料）",
    )

    # Call LLM (Gemini Flash for cost efficiency)
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        response = await client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
    except Exception as e:
        logger.warning("theme_discovery_llm_failed", error=str(e)[:100])
        return []

    new_themes = result.get("new_themes", [])
    reclassifications = result.get("reclassifications", [])

    if not new_themes and not reclassifications:
        logger.info("no_new_themes_detected")
        return []

    # Apply new themes
    themes = load_themes()
    memberships = load_memberships()
    existing_theme_ids = {t["id"] for t in themes}

    added_themes = []
    for nt in new_themes:
        theme_id = nt.get("id", "")
        if not theme_id or theme_id in existing_theme_ids:
            continue

        related_stocks = nt.get("related_stocks", [])
        if len(related_stocks) < 5:
            continue

        # Add new theme
        new_theme = {
            "id": theme_id,
            "name_zh": nt.get("name_zh", theme_id),
            "name_en": nt.get("name_en", ""),
            "stock_count": len(related_stocks),
            "sub_industries": [],
            "source": "llm_discovery",
            "discovered_at": str(date.today()),
        }
        themes.append(new_theme)
        added_themes.append(new_theme)

        # Add memberships
        for stock_id in related_stocks:
            memberships.append({
                "stock_id": stock_id,
                "theme_id": theme_id,
                "sub_industry": "",
                "source": "llm_discovery",
            })

        logger.info("new_theme_added", theme=theme_id, stocks=len(related_stocks), reason=nt.get("reason", ""))

    # Apply reclassifications
    for rc in reclassifications:
        stock_id = rc.get("stock_id", "")
        add_theme = rc.get("add_theme", "")
        if stock_id and add_theme:
            existing = any(m["stock_id"] == stock_id and m["theme_id"] == add_theme for m in memberships)
            if not existing:
                memberships.append({
                    "stock_id": stock_id,
                    "theme_id": add_theme,
                    "sub_industry": "",
                    "source": "llm_reclassification",
                })

    # Save updated files
    with open(THEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(themes, f, ensure_ascii=False, indent=2)
    with open(MEMBERSHIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(memberships, f, ensure_ascii=False, indent=2)

    logger.info("theme_discovery_complete", new_themes=len(added_themes), reclassifications=len(reclassifications))
    return added_themes


async def classify_stocks(discover: bool = False):
    """Main entry: base classification + optional dynamic discovery."""
    settings = Settings()
    provider = FinMindProvider(settings)

    # Phase 1: Base classification from FinMind
    classifications = await base_classification(provider)
    logger.info("base_done", mappings=len(classifications))

    # Phase 2: Dynamic theme discovery (LLM-powered)
    new_themes = []
    if discover and settings.gemini_api_key:
        new_themes = await discover_new_themes(provider, settings)

    return {"classifications": len(classifications), "new_themes": len(new_themes)}


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    discover_flag = "--discover" in sys.argv
    result = asyncio.run(classify_stocks(discover=discover_flag))
    print(f"Classification complete: {result}")
