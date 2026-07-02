# Feature: 題材總覽 + 產業總覽 + 產業地圖 — ✅ DONE

## Status: FULLY COMPLETE

- ✅ Level 1 (題材總覽): ThemeCards with 47 themes, search filter, stock count, drilldown to stocks, full i18n
- ✅ Level 2 (產業總覽): SectorOverview.tsx — 上游/中游/下游 tier lanes with color-coded borders
- ✅ Level 3 (產業地圖): SupplyChainGraph.tsx with SVG radial graph (in stock detail 產業分析 tab)
- ✅ Backend: `/themes`, `/themes/{id}/stocks`, `/themes/{id}/tiers`, `/themes/search`, `/themes/supply-chain/stock/{id}`
- ✅ Data: themes.json (47 themes), theme_memberships.json (6815 mappings), tier_classification.json (8 themes with tier mappings), supply_chain/relationships.json
- ✅ Flow: ThemeCards → click theme → drilldown stocks + "查看產業鏈" button → SectorOverview (tier lanes)

## Overview

These three views live INSIDE the market page's **[產業]** tab. They form a drilldown hierarchy:

```
Market → 產業 tab → 題材總覽 (theme cards grid)
                        ↓ click a theme
                    產業總覽 (sector tiers: 上游/中游/下游)
                        ↓ click "地圖"
                    產業地圖 (supply chain relationship graph)
```

## Level 1: 題材總覽 (Theme Discovery)

```
┌────────────────────────────────────────────────────────────┐
│ 🔥 今日台股產業漲幅焦點                        [漲●] [跌]  │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│ │ #1           │ │ #2           │ │ #3           │       │
│ │ +6.06%       │ │ +3.59%       │ │ +0.88%       │       │
│ │ 機殼與滑軌   │ │ 精密機構件   │ │ 氣冷核心組件 │       │
│ │ 13家         │ │ 12家         │ │ 12家         │       │
│ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                            │
│ Market: [台股●] [美股] [日股] [ETF]     ♡ 收藏             │
│ Category pills:                                            │
│ [全部●] [IC設計] [半導體製造] [先進封測] [記憶體]          │
│ [AI伺服器] [散熱冷卻] [網通衛星] [被動元件] [電子零組件]  │
│ [光學顯示] [電動車] [綠能環保] [智慧機器人] [軟體資安]    │
│ [消費終端] [多元產業]                                      │
│                                                            │
│ ┌── Theme Card ──┐ ┌── Theme Card ──┐ ┌── Theme Card ──┐ │
│ │ HPC高速運算IC  │ │ AI伺服器       │ │ 先進封裝        │ │
│ │ 12 companies   │ │ 15 companies   │ │ 8 companies    │ │
│ │ avg +2.3%      │ │ avg +1.8%      │ │ avg -0.5%      │ │
│ │ [Click→詳情]   │ │                │ │                │ │
│ └────────────────┘ └────────────────┘ └────────────────┘ │
└────────────────────────────────────────────────────────────┘
```

## Level 2: 產業總覽 (Sector Overview)

Shown when user clicks a theme card:

```
┌────────────────────────────────────────────────────────────┐
│ ← 返回題材總覽    HPC高速運算IC                            │
│                                                            │
│ ┌── 上游 ──────────────────────────────────────────────┐  │
│ │ 2330 台積電  │ 3711 日月光  │ 2303 聯電              │  │
│ │ 2295 ▼-2.9% │ 540 ▼-6.4%  │ 121 ▼-8.0%            │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
│ ┌── 中游 ──────────────────────────────────────────────┐  │
│ │ 2454 聯發科  │ 3034 聯詠   │ 6643 M31              │  │
│ │ 4070 ▼-5.4% │ 380 ▼-4.2% │ 501 ▼-8.0%            │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
│ ┌── 下游 ──────────────────────────────────────────────┐  │
│ │ 2317 鴻海    │ 2382 廣達   │ 3231 緯創              │  │
│ │ 269 ▼-5.3%  │ 376 ▼-3.6% │ 178 ▼-4.8%            │  │
│ └──────────────────────────────────────────────────────┘  │
│                                                            │
│ [查看產業地圖 →]                                           │
└────────────────────────────────────────────────────────────┘
```

## Level 3: 產業地圖 (Supply Chain Graph) — Future

Interactive node-link graph showing company relationships:
- Nodes = companies (sized by market cap)
- Edges = typed relationships (supply / customer / compete)
- Colors by tier (upstream/midstream/downstream)
- Tech: Cytoscape.js or React Flow

## Data Requirements

**For 題材總覽**: Need a themes/categories API
- Currently: We have sector data from FinMind (`/market/indices/5sec`)
- Gap: No "theme" concept (16 categories like AI伺服器, 記憶體, etc.)
- Solution: Static theme definitions + map stocks to themes via sector

**For 產業總覽**: Need company-to-tier mapping
- Gap: No upstream/midstream/downstream data in FinMind
- Solution Phase 1: Static JSON mapping (can be AI-generated from annual reports)
- Solution Phase 2: AI extraction pipeline (from agent-system.md)

**For 產業地圖**: Need relationship edges
- Gap: No company-to-company relationship data
- Solution: Future feature (requires data model from data-model.md)

## Implementation Priority

1. **題材總覽** — Can implement now with static category definitions + existing sector data
2. **產業總覽** — Needs theme-to-stock mapping (static JSON initially)
3. **產業地圖** — Future (requires relationship graph data)

## Files

- NEW: `src/components/market/ThemeCards.tsx`
- NEW: `src/components/market/SectorOverview.tsx`
- NEW: `kestrel-backend/app/api/v1/endpoints/themes.py` (static theme data)
