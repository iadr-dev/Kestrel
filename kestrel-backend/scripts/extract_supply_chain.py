"""Supply chain extraction — uses LLM to extract relationships from company descriptions.

Phase 2: Extracts supplier/customer/competitor relationships by analyzing:
1. Company profiles (main_business field from MOPS)
2. Theme memberships (which stocks share themes)
3. LLM reasoning about industry relationships

Usage: python -m scripts.extract_supply_chain [--stocks 2330,2317] [--top 50]
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"
RELATIONSHIPS_FILE = DATA_DIR / "supply_chain" / "relationships.json"
PROFILES_FILE = DATA_DIR / "company_profiles.json"

EXTRACTION_PROMPT = """你是專業的台灣股市產業分析師。根據以下公司資料，分析此公司的供應鏈關係。

分析公司: {stock_id} {company_name}
產業: {industry}
主要業務: {main_business}

同主題的其他公司（可能的上下游關係）：
{peer_stocks}

已知的供應鏈常識（台灣科技業）：
- 半導體: IC設計→晶圓代工→封裝測試→系統廠
- 電子代工: 品牌廠→EMS代工→零組件→材料
- 伺服器: 雲端廠→伺服器ODM→散熱/電源/PCB→晶片

請輸出此公司可能的供應鏈關係 JSON：
{{
  "relationships": [
    {{
      "from": "{stock_id}",
      "from_name": "{company_name}",
      "to": "對方股票代號",
      "to_name": "對方公司名稱",
      "type": "supplies|customer|competes",
      "confidence": "high|medium|low",
      "revenue_pct": null,
      "note": "關係說明"
    }}
  ]
}}

規則：
- 只列出你有信心的關係（不要猜測）
- high = 公開資訊明確揭露, medium = 產業常識可推論, low = 可能但不確定
- 每家公司最多列出5個最重要的關係
- 如果不確定，回傳空陣列
"""


def load_existing_relationships() -> list[dict]:
    if RELATIONSHIPS_FILE.exists():
        with open(RELATIONSHIPS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def load_profiles() -> dict[str, dict]:
    if PROFILES_FILE.exists():
        with open(PROFILES_FILE, encoding="utf-8") as f:
            profiles = json.load(f)
        return {p.get("stock_id", ""): p for p in profiles if p.get("stock_id")}
    return {}


def load_memberships() -> list[dict]:
    path = DATA_DIR / "theme_memberships.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


async def extract_for_stock(stock_id: str, settings: Settings, profiles: dict, memberships: list) -> list[dict]:
    """Extract supply chain relationships for a single stock using LLM."""
    profile = profiles.get(stock_id, {})
    company_name = profile.get("name_zh", stock_id)
    industry = profile.get("industry", "")
    main_business = profile.get("main_business", "")

    # Find peer stocks in same theme
    stock_themes = [m["theme_id"] for m in memberships if m["stock_id"] == stock_id]
    peers = []
    for m in memberships:
        if m["stock_id"] != stock_id and m["theme_id"] in stock_themes:
            peer_profile = profiles.get(m["stock_id"], {})
            peers.append(f"  {m['stock_id']} {peer_profile.get('name_zh', m['stock_id'])} ({m.get('sub_industry', '')})")
    peer_text = "\n".join(peers[:15]) or "（無同主題公司資料）"

    prompt = EXTRACTION_PROMPT.format(
        stock_id=stock_id,
        company_name=company_name,
        industry=industry,
        main_business=main_business or "（無資料）",
        peer_stocks=peer_text,
    )

    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        response = await client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        result = json.loads(raw)
        relationships = result.get("relationships", [])
        logger.info("extracted_relationships", stock_id=stock_id, count=len(relationships))
        return relationships
    except Exception as e:
        logger.warning("extraction_failed", stock_id=stock_id, error=str(e)[:100])
        return []


async def run_extraction(stock_ids: list[str] | None = None, top_n: int = 50):
    """Run supply chain extraction for specified stocks or top N by market cap."""
    settings = Settings()

    if not settings.gemini_api_key:
        logger.error("no_gemini_api_key")
        return []

    profiles = load_profiles()
    memberships = load_memberships()
    existing = load_existing_relationships()
    existing_pairs = {(r["from"], r["to"]) for r in existing}

    if stock_ids is None:
        # Use top stocks from profiles or fallback list
        if profiles:
            stock_ids = list(profiles.keys())[:top_n]
        else:
            stock_ids = ["2330", "2317", "2454", "2382", "2308", "3711", "2412", "3034", "2303", "6505"]

    logger.info("extraction_start", stocks=len(stock_ids))

    new_relationships = []
    for stock_id in stock_ids:
        rels = await extract_for_stock(stock_id, settings, profiles, memberships)
        for r in rels:
            pair = (r.get("from", ""), r.get("to", ""))
            reverse_pair = (r.get("to", ""), r.get("from", ""))
            if pair not in existing_pairs and reverse_pair not in existing_pairs:
                new_relationships.append(r)
                existing_pairs.add(pair)
        await asyncio.sleep(1)  # Rate limit

    # Merge with existing
    all_relationships = existing + new_relationships

    # Save
    RELATIONSHIPS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RELATIONSHIPS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_relationships, f, ensure_ascii=False, indent=2)

    logger.info("extraction_complete", new=len(new_relationships), total=len(all_relationships))
    return new_relationships


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    stocks = None
    top = 50
    for arg in sys.argv[1:]:
        if arg.startswith("--stocks"):
            stocks = sys.argv[sys.argv.index(arg) + 1].split(",")
        elif arg.startswith("--top"):
            top = int(sys.argv[sys.argv.index(arg) + 1])

    result = asyncio.run(run_extraction(stock_ids=stocks, top_n=top))
    print(f"Extracted {len(result)} new relationships")
