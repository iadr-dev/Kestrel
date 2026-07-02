# Feature Plans — Kestrel Redesign

Each feature plan details the UIUX layout, data sources, components, and integration with our existing codebase.

## Feature Breakdown

| # | File | Feature | Priority |
|---|------|---------|----------|
| 1 | `feat-market-page.md` | Market page 2-row tabs + 2-column layout | HIGH |
| 2 | `feat-stock-detail.md` | Stock detail page consolidation (11→7 tabs) + enrichment | HIGH |
| 3 | `feat-ai-analysis.md` | AI Analysis page (scoring + rankings) | MEDIUM |
| 4 | `feat-navigation.md` | Left sidebar nav update | HIGH |
| 5 | `feat-themes-industry.md` | 題材總覽 + 產業總覽 + 產業地圖 (inside market) | MEDIUM |
| 6 | `feat-heatmap.md` | Full-page heatmap (inside market tab) | MEDIUM |
| 7 | `feat-data-pipeline.md` | Scheduled jobs + data ingest + supply chain + theme classification | HIGH |
| 8 | `feat-agent-system.md` | Dual-mode agent (conversational + batch AI scoring) | MEDIUM |
| 9 | `feat-architecture-optimization.md` | Performance: React Query + Redis + cache strategy + Docker | **CRITICAL** |
| 10 | `feat-gap-analysis.md` | Full gap analysis: what's done, what's missing, priority queue | REFERENCE |
| 11 | `feat-supply-chain.md` | Supply chain data: themes, memberships, relationships, graph | **HIGH (Moat)** |
| 12 | `feat-self-built-data.md` | US fundamentals scraper + Company profiles + Theme classification (surpass aistockmap) | **HIGH** |
| 13 | `feat-agent-audit.md` | Agent system audit: 18 issues found, lifecycle, comparison with Claude.ai/ChatGPT | **HIGH** |
| 14 | `feat-pet-audit.md` | Pet system audit: 5 critical bugs, gacha math, race conditions | MEDIUM |

## Reference Materials

- `/Desktop/Meta/Mystock/*.md` — Architecture, data model, design system specs
- `/Desktop/Meta/Mystock/個股資訊/` — Stock detail page screenshots
- `/Desktop/Meta/Mystock/每日焦點/` — Daily focus page screenshots
- `/Desktop/Meta/Mystock/熱力圖/` — Heatmap screenshots
- `/Desktop/Meta/Mystock/題材總覽/` — Theme overview screenshots
- `/Desktop/Meta/Mystock/AI分析/` — AI scoring screenshots

## Current Project Code References

- Backend: `kestrel-backend/app/api/v1/endpoints/` (130+ endpoints)
- Frontend components: `kestrel-web/src/components/market/` (23 components)
- Stock components: `kestrel-web/src/components/stock/` (13 components)
- Market page: `kestrel-web/src/app/dashboard/market/page.tsx`
- Stock page: `kestrel-web/src/app/dashboard/stocks/[id]/page.tsx`
