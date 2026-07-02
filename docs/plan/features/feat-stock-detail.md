# Feature: Stock Detail Page Redesign — ✅ DONE

## Status: FULLY COMPLETE

- ✅ 7-tab consolidation (info/industry/financial/chips/technical/news/research)
- ✅ KPI grid in 基本資料 tab (PER, PBR, dividend yield, market cap)
- ✅ Company profile in 基本資料 (chairman, CEO, HQ, founded, listed, capital, website, business) — fetched from `/themes/company/{id}/profile`
- ✅ AI summary + SWOT + factors in 產業分析 tab (AISummarySection)
- ✅ Supply chain graph in 產業分析 tab (SupplyChainGraph)
- ✅ Merged revenue + financials + profit + dividend into 財務分析
- ✅ 籌碼分析 with sub-tabs: 三大法人 / 大戶資訊 / 融資融券 (ChipAnalysisSection)
- ✅ Shareholding distribution (retail/mid/whale %) with progress bars
- ✅ All text uses i18n (profile_*, ai_*, chip_* namespaces in stock section)

## Overview

Consolidate current 11 tabs into 7 richer tabs. Keep ALL existing data, merge related views, and add new information from the reference design (AI summary, SWOT, KPI grid, shareholder distribution).

## Current State (11 Tabs)

```
[K線] [多空] [即時] [法人] [營收] [財報] [獲利] [除權息] [行事曆] [新聞] [個股資訊]
```

## Target State (7 Tabs)

```
[基本資料] [產業分析] [財務分析] [籌碼分析] [技術分析] [相關新聞] [研究圖表]
```

## Tab Details

### Tab 1: 基本資料

```
┌────────────────────────────────────────────────────────────┐
│ Company Header                                              │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ M31 (6643)                              ♡ 加入收藏     ││
│ │ 市值: 234.0億  產業: 半導體  成立: 2011  董事長: 陳慧玲 ││
│ │ 總部: 新竹縣竹北市台元二街8號9樓                        ││
│ │ 官網: https://www.m31tech.com                           ││
│ └─────────────────────────────────────────────────────────┘│
│                                                            │
│ 📊 最新財務概況 (2026年 Q1)                                │
│ ┌──────────┬──────────┬──────────┬──────────┐             │
│ │ 季營收    │ 市值      │ 本益比    │ 股價淨值比│             │
│ │ 3.9億    │ 234.0億  │ 332.93x │ 12.90x  │             │
│ │ ▼-9.2%   │          │          │          │             │
│ ├──────────┼──────────┼──────────┼──────────┤             │
│ │ 毛利率    │ 營益率    │ 淨利率    │ EPS      │             │
│ │ 100%     │ -16.79%  │ -12.48%  │ -1.18元  │             │
│ └──────────┴──────────┴──────────┴──────────┘             │
│                                                            │
│ 📋 重大資訊觀測站 (MOPS)                      [Premium]     │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ • 財務揭露 / 法說會動態 / 董事會決議                    ││
│ │ (sorted by date, premium-gated deep content)            ││
│ └─────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
```

**Data sources**: Existing `StockInfoTab` + `/fundamentals/{id}/revenue` + `/fundamentals/{id}/market-value` + `/stocks/{id}/per`

### Tab 2: 產業分析

```
┌────────────────────────────────────────────────────────────┐
│ 🏷️ 客製 ASIC 與矽智財                        [高關聯度]    │
│                                                            │
│ ✨ AI 智能摘要                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ M31 (6643) FY2025 營收 17.82 億元創歷史新高，2026年    ││
│ │ 為「權利金收割年」，4月營收年增30%強勁回升...           ││
│ └─────────────────────────────────────────────────────────┘│
│                                                            │
│ 📍 市場定位                                                │
│ • 利基專精: 台灣先進製程實體IP需求供應鏈...                │
│                                                            │
│ 🔬 技術重心                                    [🔒Premium] │
│ 📦 主要產品                                    [🔒Premium] │
│ 👥 主要客戶                                    [🔒Premium] │
│                                                            │
│ 📊 SWOT 分析                                              │
│ ┌───────────────────┬───────────────────┐                 │
│ │ 優勢 (S)          │ 劣勢 (W)          │                 │
│ │ • ...             │ • ...             │                 │
│ ├───────────────────┼───────────────────┤                 │
│ │ 機會 (O)          │ 威脅 (T)          │                 │
│ │ • ...             │ • ...             │                 │
│ └───────────────────┴───────────────────┘                 │
│                                                            │
│ ⚡ 多空訊號 (from existing BullBearTab)                    │
│ [多方訊號 cards] [空方訊號 cards]                           │
└────────────────────────────────────────────────────────────┘
```

**Data sources**: NEW AI-generated content + existing `BullBearTab` data

### Tab 3: 財務分析

Merge: 營收 + 財報 + 獲利 + 除權息 → single scrollable view

```
┌────────────────────────────────────────────────────────────┐
│ 📈 投資收益 (Dividend chart - existing DividendTab)        │
│ [bar chart: 現金股利 + 股票股利 by year]                   │
│ [table: 年度/現金/股票/合計/年殖利率]                      │
│                                                            │
│ 📊 營收分析趨勢 (existing RevenueTab)                      │
│ [bar chart: quarterly revenue with YoY growth line]        │
│ [table: 年度/季營收(億)/年增率%]                           │
│                                                            │
│ 📉 獲利能力趨勢 (existing ProfitTab)                       │
│ [multi-line chart: 毛利率/營益率/淨利率 by quarter]        │
│ [table: 季度/毛利率/營益率/淨利率/EPS]                     │
│                                                            │
│ 📋 財務報表 (existing FinancialsTab - condensed)           │
│ [Income statement / Balance sheet toggle]                   │
└────────────────────────────────────────────────────────────┘
```

**Data sources**: Existing `RevenueTab` + `ProfitTab` + `DividendTab` + `FinancialsTab`

### Tab 4: 籌碼分析

Merge: 法人 + (new shareholder distribution)

```
┌────────────────────────────────────────────────────────────┐
│ 👥 籌碼分析                                                │
│ [大戶資訊] [三大法人] [融資融券] ← sub-tabs                │
│                                                            │
│ 散戶(≤50張)  中實戶(50~400張)  大戶(>400張)              │
│                                                            │
│ 持股人數趨勢 (line chart: 散戶/中實戶/大戶 over time)      │
│                                                            │
│ 大戶資訊 (table: date / 大戶人數 / 中實戶 / 散戶 / 總計)  │
│                                                            │
│ ─── OR (sub-tab: 三大法人) ───                            │
│ Existing InstitutionalTab content                          │
│                                                            │
│ ─── OR (sub-tab: 融資融券) ───                            │
│ Existing margin data                                       │
└────────────────────────────────────────────────────────────┘
```

**Data sources**: Existing `InstitutionalTab` + `/institutional/shareholding-per/{id}` + `/institutional/margin/{id}`

### Tab 5: 技術分析

Enhanced K-line (existing `KLineChart` + additions)

```
┌────────────────────────────────────────────────────────────┐
│ [K線●] [河流圖]                                            │
│                                                            │
│ M31 (6643) 技術分析  ●● 紅漲綠跌                          │
│                                                            │
│ 時間: [時] [日●] [週] [月] [1M] [3M] [6M] [YTD] [1Y] [5Y]│
│ 均線: ☑MA5 ☑MA10 ☑MA20 ☐MA60 ☐MA240                     │
│ 副圖: ☐BB(20) ☐三大法人 ☐大戶持股                        │
│ 畫線: ☑趨勢線  一水平線  ✕刪除  [colors]                 │
│ 重大資訊: ●澄清回應 ●財務數據 ●公司治理 ●重大事件        │
│                                                            │
│ [===== K-LINE CHART (full width, 400px height) =====]     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Data sources**: Existing `KLineChart` component + existing price endpoints

### Tab 6: 相關新聞

```
[即時新聞●] [財經新聞] [⚙️]

Premium gate banner for deep financial news

• Article title (source · date) [↗]
• Article title (source · date) [↗]
• ...
```

**Data sources**: Existing `NewsTab` + `/stocks/{id}/news`

### Tab 7: 研究圖表

Placeholder for future community feature.

```
此公司尚未有研究圖表
點擊下方按鈕讓我們知道你的需求，越多人支持越快安排！
[已登記需求 · 已有 N 人支持]
```

## Existing Components Mapping

| New Tab | Reuses Components |
|---------|-------------------|
| 基本資料 | `StockInfoTab` (enhanced) |
| 產業分析 | `BullBearTab` + NEW AI section |
| 財務分析 | `RevenueTab` + `FinancialsTab` + `ProfitTab` + `DividendTab` |
| 籌碼分析 | `InstitutionalTab` + NEW shareholder section |
| 技術分析 | `KLineChart` (enhanced) |
| 相關新聞 | `NewsTab` |
| 研究圖表 | NEW placeholder |

## Files to Modify

- `src/app/dashboard/stocks/[id]/page.tsx` — Tab restructure
- `src/components/stock/StockInfoTab.tsx` — Add KPI grid
- NEW: `src/components/stock/IndustryAnalysisTab.tsx`
- NEW: `src/components/stock/FinancialAnalysisTab.tsx` (combines 4 tabs)
- NEW: `src/components/stock/ChipAnalysisTab.tsx` (combines institutional + margin)
