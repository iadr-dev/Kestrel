# Feature: Supply Chain Data — ✅ FULLY DONE

## Status: FULLY COMPLETE

- ✅ Phase 1 (Seed data): `relationships.json` (15 edges), `themes.json` (47), `theme_memberships.json` (6815)
- ✅ Phase 2 (LLM extraction): `scripts/extract_supply_chain.py` — Gemini Flash analyzes company profiles + peer stocks to extract relationships
- ✅ API: `/supply-chain/stock/{id}`, `/supply-chain/graph/{id}`, `/themes/{id}/tiers`
- ✅ Frontend: SupplyChainGraph.tsx (reagraph force-directed 2D graph), SectorOverview.tsx (tier lanes)
- ✅ reagraph installed (^4.30.8) — professional WebGL graph with force-directed layout, edge labels (i18n), draggable nodes
- ✅ SQLAlchemy models: `ThemeMembership` + `SupplyChainEdge` in `app/models/supply_chain.py` (PostgreSQL-ready)
- ✅ Dynamic growth: Weekly theme discovery + extraction pipeline can grow the graph over time
- ⏭️ Phase 3 (Admin review queue): Not needed yet — low volume of extractions

## Why This Matters

This is the **#1 differentiator** vs generic stock tools. No API provides "who supplies who" — it must be built. aistockmap.com's main moat is their manually curated supply chain graph. We need our own.

## Data Sources for Supply Chain

### Where relationships are disclosed (Taiwan public companies)

| Source | Content | Format | Access |
|--------|---------|--------|--------|
| **年報 (Annual Report)** Chapter 2「營業概況」 | 主要客戶 (>10% revenue MUST disclose), 主要供應商 | PDF on MOPS | Free, public |
| **法說會簡報** (Earnings call slides) | Supply chain diagrams, customer logos | PDF/PPT on company IR sites | Free |
| **MOPS 重大訊息** | New customer wins, supply agreements | Text | Scraper needed |
| **MoneyDJ 產業鏈** | Pre-curated upstream/midstream/downstream | Web page | Scrape or reference |
| **Yahoo 概念股** | Stock groupings by theme | Web | Reference only |
| **CMoney 產業鏈** | Similar to MoneyDJ | Premium API | $$$ |
| **Bloomberg SPLC** | Global supply chain edges | Terminal only | $$$$$ |

### What we can extract

```
(台積電 2330) ──[supplies to]──→ (蘋果 AAPL)     revenue: ~25%
(台積電 2330) ──[supplies to]──→ (輝達 NVDA)     revenue: ~15%  
(ASML) ──────[supplies to]──→ (台積電 2330)     critical equipment
(日月光 3711) ──[competes]───→ (矽品 *merged*)
(聯發科 2454) ──[customer of]──→ (台積電 2330)   foundry service
```

## Implementation Strategy (3 Phases)

### Phase 1: Seed Data from FinMind Full Stock Pool (Week 1-2)

Since we fetch ALL TW/US stocks at initialization (FinMind `TaiwanStockInfo` + `USStockInfo` + `TaiwanStockIndustryChain`), we already have a complete stock pool with industry/sub-industry classification. Build theme memberships for ALL stocks, not just top 50:

```json
// data/supply_chain/relationships.json
[
  {
    "from": "2330",
    "from_name": "台積電",
    "to": "AAPL",
    "to_name": "Apple",
    "type": "supplies",
    "confidence": "high",
    "source": "annual_report_2025",
    "revenue_pct": 25,
    "note": "A16/A17 chip foundry"
  },
  {
    "from": "ASML",
    "from_name": "ASML",
    "to": "2330",
    "to_name": "台積電",
    "type": "supplies",
    "confidence": "high",
    "source": "public_knowledge",
    "note": "EUV lithography equipment"
  }
]

// data/supply_chain/memberships.json
[
  {
    "stock_id": "2330",
    "theme": "半導體製造",
    "tier": "midstream",
    "role": "晶圓代工",
    "relevance": "core"
  },
  {
    "stock_id": "2454",
    "theme": "IC設計",
    "tier": "upstream",
    "role": "手機/WiFi晶片設計",
    "relevance": "core"
  }
]
```

**Data pipeline for theme memberships:**
1. **FinMind `TaiwanStockIndustryChain`** — Fetch ALL stocks' industry/sub_industry → base layer (Layer 1)
2. **FinMind `TaiwanStockInfo`** — stock_id + stock_name + industry_category for full pool
3. **LLM batch classification** — Classify ALL ~1800 TW stocks into our 16 themes using Gemini Flash (cost: ~$0.50 total)
4. **Supply chain edges** — Start with top 100 stocks manually + LLM extraction from annual reports
5. **TWSE sector indices** (from 5-sec index — we already fetch these) — daily sector performance

**For supply chain edges (Company↔Company), start with:**
1. Common knowledge (TSMC→Apple, MediaTek→TSMC, etc.) — ~50 edges manually
2. MoneyDJ 產業鏈頁面 (scrape tier structure for reference)
3. Top 100 stocks' annual reports (主要客戶/供應商 sections via LLM extraction)
4. Gradually expand via LLM extraction pipeline

### Phase 2: LLM Extraction (Week 3-4)

Automated pipeline to extract from annual reports:

```python
# scripts/extract_supply_chain.py

async def extract_from_annual_report(stock_id: str, report_text: str):
    """Extract supply chain relationships from annual report text."""
    
    prompt = """
    從以下年報「營業概況」章節中，抽取供應鏈關係。
    
    輸出格式 (JSON array):
    [
      {
        "from": "本公司股票代號",
        "to": "對方公司名稱或代號",
        "type": "supplies | customer | competes",
        "revenue_pct": 數字或null,
        "description": "關係描述"
      }
    ]
    
    規則:
    - 只抽取明確提到的關係，不要推測
    - 「主要客戶」= 本公司 supplies to 客戶
    - 「主要供應商」= 供應商 supplies to 本公司
    - 營收佔比如果有提到就填，沒有就 null
    
    年報內容:
    {report_text}
    """
    
    result = await llm_generate(
        model="gemini-2.5-flash",
        prompt=prompt,
        schema=RELATIONSHIP_SCHEMA,
    )
    
    return result
```

**Annual report acquisition:**
- MOPS (公開資訊觀測站): `https://mops.twse.com.tw/` → 年報下載
- Parse PDF → extract Chapter 2 text
- Feed to LLM for relationship extraction

### Phase 3: Human Review + Continuous Update (Ongoing)

```python
# Admin review queue
@router.get("/admin/supply-chain/review-queue")
async def get_review_queue():
    """Low-confidence extractions that need human verification."""
    return await db.query(
        "SELECT * FROM relationships WHERE confidence = 'low' AND reviewed = false"
    )

@router.put("/admin/supply-chain/verify/{id}")
async def verify_relationship(id: str, is_correct: bool):
    """Human verifies or rejects an LLM-extracted relationship."""
    ...
```

## Database Schema

```sql
-- Theme/category definitions
CREATE TABLE themes (
    id VARCHAR(50) PRIMARY KEY,        -- e.g., "ai_server"
    name_zh VARCHAR(100) NOT NULL,     -- "AI伺服器"
    name_en VARCHAR(100),              -- "AI Server"
    category VARCHAR(50),              -- "半導體" parent category
    description TEXT,
    stock_count INTEGER DEFAULT 0,
    avg_change_pct FLOAT DEFAULT 0     -- updated daily
);

-- Stock ↔ Theme membership (many-to-many)
CREATE TABLE theme_memberships (
    id VARCHAR(36) PRIMARY KEY,
    stock_id VARCHAR(20) NOT NULL,
    theme_id VARCHAR(50) NOT NULL,
    tier VARCHAR(20),                  -- "upstream" | "midstream" | "downstream"
    role VARCHAR(100),                 -- "晶圓代工" | "IC設計" | "封裝測試"
    relevance VARCHAR(20) DEFAULT 'related',  -- "core" | "related" | "peripheral"
    source VARCHAR(50),                -- "manual" | "llm_extracted" | "moneydj"
    created_at DATETIME,
    UNIQUE(stock_id, theme_id)
);

-- Company ↔ Company relationships (supply chain edges)
CREATE TABLE supply_chain_edges (
    id VARCHAR(36) PRIMARY KEY,
    from_stock_id VARCHAR(20) NOT NULL,
    from_name VARCHAR(100),
    to_stock_id VARCHAR(20) NOT NULL,
    to_name VARCHAR(100),
    relationship_type VARCHAR(20) NOT NULL,  -- "supplies" | "customer" | "competes" | "partner"
    revenue_pct FLOAT,                       -- % of from's revenue from this relationship
    confidence VARCHAR(10) DEFAULT 'medium', -- "high" | "medium" | "low"
    source VARCHAR(50),                      -- "annual_report" | "news" | "manual" | "llm"
    source_detail TEXT,                      -- specific document reference
    verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(50),
    created_at DATETIME,
    updated_at DATETIME
);
```

## API Endpoints

```python
# Supply chain endpoints
GET /api/v1/supply-chain/themes                    # All themes with stock counts
GET /api/v1/supply-chain/themes/{theme_id}/stocks  # Stocks in a theme (with tiers)
GET /api/v1/supply-chain/stock/{stock_id}/edges    # Relationships for one stock
GET /api/v1/supply-chain/stock/{stock_id}/themes   # Themes a stock belongs to
GET /api/v1/supply-chain/graph/{theme_id}          # Full graph data for visualization
```

## Frontend Components

### In Market Page (產業 tab)

```
ThemeCards.tsx → shows all 16 themes with avg performance
    ↓ click
SectorOverview.tsx → shows stocks by tier (上游/中游/下游 lanes)
    ↓ click "查看地圖"
SupplyChainGraph.tsx → interactive 3D/2D node-link diagram (reagraph)
```

### Graph Library: reagraph (https://github.com/reaviz/reagraph)

Why reagraph over Cytoscape.js:
- **React-native**: Components, not imperative API — fits our Next.js stack perfectly
- **3D support**: WebGL-powered, can do 3D force-directed graphs
- **TypeScript**: Full type safety
- **Lightweight**: No jQuery dependency (unlike Cytoscape)
- **Beautiful defaults**: Looks modern out of the box
- **Edge labels**: Supports typed edge labels (供應/競合/客戶)

```tsx
import { GraphCanvas, GraphEdge, GraphNode } from 'reagraph';

const nodes: GraphNode[] = [
  { id: '2330', label: '台積電', data: { tier: 'midstream', size: 'large' } },
  { id: '2454', label: '聯發科', data: { tier: 'upstream' } },
  { id: 'NVDA', label: 'NVIDIA', data: { tier: 'downstream' } },
];

const edges: GraphEdge[] = [
  { id: 'e1', source: '2454', target: '2330', label: '客戶' },
  { id: 'e2', source: '2330', target: 'NVDA', label: '供應' },
];

<GraphCanvas nodes={nodes} edges={edges} />
```

### In Stock Detail Page (產業分析 tab)

```
- "所屬題材": list of themes this stock belongs to
- "供應鏈位置": upstream/midstream/downstream badge
- "主要客戶": relationship cards (with revenue %)
- "主要供應商": relationship cards
- "競爭對手": relationship cards
```

## Data Volume Estimate

| Entity | Count | Source |
|--------|-------|--------|
| Themes | 16 categories | Static definition |
| Stock pool (TW) | ~1800 | FinMind TaiwanStockInfo (fetched at init) |
| Stock pool (US) | ~8000 | FinMind USStockInfo (fetched at init) |
| Theme memberships | ~3600 (1800 TW stocks × 2 themes avg) | LLM classification of full pool |
| Supply chain edges | ~100 initially → 2000+ over time | Manual + LLM extraction |
| Stocks with tier mapping | All 1800 TW initially | FinMind IndustryChain + LLM |

## Cost

| Phase | Cost | Time |
|-------|------|------|
| Phase 1 (manual seed) | $0 (human time only) | 2-3 days research |
| Phase 2 (LLM extraction from 100 annual reports) | ~$2 (Gemini Flash) | 1 day setup |
| Phase 3 (review queue) | $0 (admin UI) | Ongoing |

## Files

### Backend
- NEW: `app/api/v1/endpoints/supply_chain.py`
- NEW: `app/models/supply_chain.py` (SQLAlchemy models)
- NEW: `scripts/extract_supply_chain.py` (LLM extraction pipeline)
- NEW: `data/supply_chain/relationships.json` (seed data)
- NEW: `data/supply_chain/memberships.json` (seed data)
- NEW: `data/supply_chain/themes.json` (16 theme definitions)

### Frontend
- NEW: `src/components/market/ThemeCards.tsx`
- NEW: `src/components/market/SectorOverview.tsx`
- NEW: `src/components/market/SupplyChainGraph.tsx` (Cytoscape.js or React Flow)
- MODIFY: `src/components/stock/IndustryAnalysisTab.tsx` (show relationships)

## Priority in Overall Plan

Move from "LOW/Future" to **Week 2-3**:
- Week 2: Define themes JSON + seed memberships for top 50 stocks (manual)
- Week 3: Build API endpoints + ThemeCards UI + SectorOverview
- Week 4: LLM extraction pipeline for annual reports
- Ongoing: Human review + expand coverage
