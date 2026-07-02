# Feature: AI Analysis Page — ✅ FULLY DONE

## Status: COMPLETE (Professional-Grade)

- ✅ Page with sort tabs (Overall/Technical/Chip/Fundamental/Theme) — all i18n
- ✅ Backend: `GET /ai/rankings` reads pre-computed DuckDB scores (fallback on-the-fly)
- ✅ Backend: `GET /ai/summary/{id}` returns LLM-generated SWOT + factors
- ✅ Backend: `GET /ai/score/{id}` returns individual stock 4-factor breakdown
- ✅ Daily scoring cron at 19:30 TW persists to `stock_scores` table
- ✅ Professional scoring algorithms (institutional-grade):
  - Technical: MA alignment + RSI + MACD + volume confirmation + breakout
  - Chip: Net buying streak + amount trend + foreign dominance + breadth
  - Fundamental: YoY magnitude + acceleration + consistency + trajectory
  - Theme: Sector momentum + breadth + relative strength + acceleration
- ✅ Full i18n: `ai.title`, `ai.sort_*`, `ai.score_*`, `ai.no_data`, `ai.no_data_hint`

## Overview

New left-nav page: AI-powered stock scoring and ranking leaderboard. Multi-factor analysis (技術面/籌碼面/基本面/題材面) with overall scores. Users can see which stocks the AI rates highest.

## Reference

From `/Desktop/Meta/Mystock/AI分析/`: AI 評分排行榜 with:
- Overall score (0-100)
- Per-factor breakdown (題材面, 基本面, 技術面, 籌碼面)
- Progress bars per factor
- Sortable by: 強勢排行, 趨勢排行, 全部排行
- Tab: 我的分析 (user's saved stocks)

## Page Layout

```
┌────────────────────────────────────────────────────────────┐
│ ✨ AI 評分排行榜 ✨                                         │
│ 來自 AI 多因子分析結果，每日更新                            │
│                                                            │
│ [我的分析] [▶ 強勢排行●] [↗ 趨勢排行] [全部排行]          │
│                                                            │
│ Filters: [即時觀點▼] [中期觀望▼] [全部觀望▼]              │
│ Last updated: 下午4:28:15                    [▶ 重新整理]  │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ ┌─ #1 ────────────────────────────────────────────────┐   │
│ │ 🔥 2317 鴻海                               91.0    │   │
│ │                                                      │   │
│ │ 題材面 ████████████████████░░░ 95                    │   │
│ │ 基本面 ██████████████████░░░░░ 90                    │   │
│ │ 技術面 ████████████████░░░░░░░ 75                    │   │
│ │ 籌碼面 █████████████████████░░ 97                    │   │
│ │                                        [📊 查看分析] │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                            │
│ ┌─ #2 ────────────────────────────────────────────────┐   │
│ │ 🔥 3231 緯創                               91.0    │   │
│ │ ...                                                  │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                            │
│ ┌─ #3 ────────────────────────────────────────────────┐   │
│ │    3135 凌航                               88.0    │   │
│ │ ...                                                  │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                            │
│ [Load more...]                                             │
└────────────────────────────────────────────────────────────┘
```

## Scoring Logic (Backend)

Each stock gets 4 dimension scores (0-100):

| Dimension | Inputs | Weight |
|-----------|--------|--------|
| 題材面 | Theme relevance, sector momentum, news sentiment | 25% |
| 基本面 | Revenue YoY, EPS trend, margin expansion, P/E vs sector | 25% |
| 技術面 | MA position, RSI, volume trend, breakout signals | 25% |
| 籌碼面 | Institutional buying streak, major holder increase, margin ratio | 25% |

Overall score = weighted average of 4 dimensions.

## Backend Implementation

New endpoint: `GET /ai/rankings?sort=strong|trend|all&limit=20`

Computation: DuckDB pre-computed daily (like backtest). Uses existing data from:
- `/institutional/buy-sell/{id}` (籌碼)
- `/stocks/{id}/price` + indicators (技術)
- `/fundamentals/{id}/revenue` (基本)
- `/market/indices/5sec` sector performance (題材)

## Files

- NEW: `src/app/dashboard/ai-analysis/page.tsx`
- NEW: `src/components/ai/RankingCard.tsx`
- NEW: `kestrel-backend/app/api/v1/endpoints/ai_analysis.py`
- NEW: `kestrel-backend/app/services/ai_scoring.py`

## Data Sources

All from existing FinMind data (no new APIs needed):
- Price + indicators → technical score
- Revenue + financials → fundamental score  
- Institutional flow + shareholding → chip score
- Sector 5-sec performance + news → theme score
