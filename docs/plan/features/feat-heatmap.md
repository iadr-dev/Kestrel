# Feature: Full-Page Heatmap — ✅ FULLY DONE

## Status: COMPLETE

- ✅ Full-page mode: 30 sectors in 5x6 grid (vs 12 in compact mode)
- ✅ Color: Red=up, Green=down (TW convention) with 5-step intensity
- ✅ Time range toggle: 1D/1W/1M (i18n: 今日/一週/一月)
- ✅ View toggle: Grid (▦) / Bar chart (▥) in full-page mode
- ✅ Bar chart view: horizontal bars sorted by change%, bi-directional from center
- ✅ Click navigation: each sector → `/dashboard/market?view=industry&theme={id}`
- ✅ Tooltip: native `title` attribute shows sector name + precise change%
- ✅ Size proportional to volume (top 2 sectors get 2x2 cells)
- ✅ i18n: sector names (EN/ZH-TW), time range labels, header

## Overview

The **[熱力圖]** tab in the market page shows a full-width interactive treemap heatmap of the market. Based on reference from `/Desktop/Meta/Mystock/熱力圖/`.

## Layout

```
┌────────────────────────────────────────────────────────────┐
│ 台股產業市場熱力圖                                          │
│ 依產業平均漲跌幅度(絕對值)顯示區塊大小，顏色深淺代表漲跌   │
│ 方向與強度。點擊產業可直接進入該主題總覽。                   │
│                                                            │
│ 資料更新時間: 下午1:37:13                                   │
│                                                            │
│ View: [圖●] [柱]    Market: [台股●] [美股] [日股] [ETF]    │
│ Time: [日●] [半週] [週] [月]                               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌──────────────────────┐ ┌────────┐ ┌────────┐ ┌───────┐ │
│ │                      │ │ 顯示晶片│ │AI 伺服器│ │網通科技│ │
│ │    半導體製造         │ │ IC     │ │ +0.2%  │ │-1.2%  │ │
│ │    -2.1%             │ │ -1.3%  │ └────────┘ └───────┘ │
│ │                      │ └────────┘ ┌────────┐ ┌───────┐ │
│ │                      │ ┌────────┐ │電源穩壓 │ │面板產業│ │
│ └──────────────────────┘ │ HPC    │ │-0.5%   │ │-3.1%  │ │
│ ┌──────────┐ ┌─────────┐│ -0.8%  │ └────────┘ └───────┘ │
│ │ 封測產業  │ │ 記憶體  │└────────┘                       │
│ │ -4.1%    │ │ -1.5%   │          ┌────────────────────┐ │
│ └──────────┘ └─────────┘          │  (more sectors...) │ │
│                                    └────────────────────┘ │
│                                                            │
│ Legend: [跌超3%] ■■■■■■■■ [漲超3%]                         │
│         (green)              (red)                          │
└────────────────────────────────────────────────────────────┘
```

## Features

- **Size**: Proportional to trading volume or market cap
- **Color**: Red = up (Taiwan convention), Green = down. Intensity by % magnitude
- **Click**: Navigate to that sector's 產業總覽 (theme detail)
- **柱 view**: Alternative bar chart sorted by change%
- **Time toggle**: Show daily / half-week / weekly / monthly performance

## Enhancements over Current TreemapHeat

Current `TreemapHeat.tsx` is a small card with 12 cells. The full-page version needs:
- More sectors (30+)
- Proper treemap algorithm (squarified)
- Click interactions
- Time range controls
- List/bar alternative view
- Tooltip on hover with details

## Data Source

- `GET /market/indices/5sec` — Sector 5-second data (during trading hours)
- Fallback: Use previous day's close-to-close for non-trading hours

## Files

- Modify: `src/components/market/TreemapHeat.tsx` — Add `fullPage` prop for expanded mode
- OR NEW: `src/components/market/FullHeatmap.tsx` — Dedicated full-page component
