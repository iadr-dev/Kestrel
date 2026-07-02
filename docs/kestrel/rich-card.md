# Rich Card Testing Guide

Manual test prompts for every agent rich card. Open `/dashboard/chat`, paste each
prompt (primary locale is zh-TW), and check the card renders as described.

## How rich cards work (1-paragraph recap)

The agent calls a `render_*` tool → backend emits a `rich_card` SSE event
`{type:"rich_card", card_type, ...data}` → frontend injects `[RICH_CARD:{json}]`
into the message text → `MessageBubble.RichContent` parses it and switches on
`card_type` to render the matching component (`src/components/chat/rich-cards/`).

**If a card does NOT appear:** the agent chose plain text instead (card emission is
LLM-driven, not guaranteed). Re-ask more explicitly (e.g. add 「用卡片呈現」/「畫出來」)
or pick a clearer trigger below. A *registered & wired* card can still be skipped by
the model — that's expected, not a bug. Tier note: `subagent`/`team` framework is
premium/pro; a free account may answer simpler.

## Testing checklist per card

| # | Card | `card_type` | Owning skill | Component |
|---|------|-------------|--------------|-----------|
| 1 | Stock analysis card | `stock_analysis` | stock_analysis | `StockCard.tsx` |
| 2 | Stock comparison row | `stock_comparison` | (legacy alias) | `StockCardRow.tsx` |
| 3 | Comparison table | `comparison_table` | compare_stocks / screener | `rich-cards/ComparisonTable.tsx` |
| 4 | Score gauge | `score` | stock_analysis / chip_flow | `rich-cards/ScoreGauge.tsx` |
| 5 | Mini chart | `chart` | many (trend viz) | `rich-cards/MiniChart.tsx` |
| 6 | Alert confirm | `alert_confirm` | alert_setup | `rich-cards/AlertConfirmCard.tsx` |
| 7 | Supply chain | `supply_chain` | company_research | `rich-cards/SupplyChainCard.tsx` |
| 8 | Theme overview | `theme_overview` | company_research | `rich-cards/ThemeOverviewCard.tsx` |
| 9 | K-line chart | `kline_chart` | stock_analysis | `rich-cards/KlineChart.tsx` |
| 10 | Institutional flow | `institutional_flow_trend` | chip_flow | `rich-cards/InstitutionalFlowCard.tsx` |
| 11 | Financial statement | `financial_statement` | earnings_review | `rich-cards/FinancialStatementCard.tsx` |
| 12 | Dividend history | `dividend_history` | earnings_review | `rich-cards/DividendHistoryCard.tsx` |
| 13 | Short position trend | `short_position_trend` | chip_flow | `rich-cards/ShortPositionCard.tsx` |
| 14 | Options sentiment | `options_sentiment` | market_briefing | `rich-cards/OptionsSentimentCard.tsx` |
| 15 | ESG scorecard | `esg_scorecard` | company_research | `rich-cards/EsgScorecardCard.tsx` |
| 16 | ETF profile | `etf_profile` | stock_analysis (ETF) | `rich-cards/EtfProfileCard.tsx` |
| 17 | Active ETF holders | `active_etf_holders` | chip_flow (ETF) | `rich-cards/ActiveEtfHoldersCard.tsx` |
| 18 | Shareholder gift | `shareholder_gift` | corporate_actions | `rich-cards/ShareholderGiftCard.tsx` |

> Backend exposes 17 `render_*` tools; the frontend ships 16 rich-card components
> (`stock_comparison` is a legacy alias with no dedicated card — see #2).

---

## 1. Stock analysis card — `stock_analysis`

**Prompt:** `幫我分析台積電 2330，用卡片呈現`

**Expect:** A card with stock name/code, current price + change% (colored), a 20-day
sparkline, OHLC candlestick beside the name, a 9-metric grid (前收/市值/開盤/本益比/...),
and a `查看詳情 →` link to `/dashboard/stocks/2330`.

---

## 2. Stock comparison row — `stock_comparison`

> Legacy alias — the backend does not actively emit this `card_type` (no render
> tool produces it). Prefer the comparison table (#3) for multi-stock side-by-side.
> Listed for completeness; expect #3 to fire instead.

---

## 3. Comparison table — `comparison_table`

**Prompt:** `比較台積電 2330 跟聯發科 2454 的本益比、營收成長、外資買賣超`

**Expect:** A side-by-side table — header `Compare: 2330 vs 2454` with each code
linking to its detail page, metric rows (P/E, Rev YoY, Foreign net…), cells colored
green/red by sign.

---

## 4. Score gauge — `score`

**Prompt:** `台積電 2330 的 AI 評分多少？各面向分數用圖呈現`

**Expect:** A gauge card: large overall score /100 (colored), plus horizontal bars
for 技術面 / 籌碼面 / 基本面 / 題材 sub-scores.

---

## 5. Mini chart — `chart`

**Prompt:** `台積電 2330 近半年的月營收趨勢，用長條圖`

**Expect:** An inline bar/line/area chart with a title, x-axis labels, bars colored
by sign. (Also fires for sector performance, breadth, generic trends.)

---

## 6. Alert confirm — `alert_confirm`

**Prompt:** `台積電 2330 漲到 1100 元提醒我`  → confirm the clarification if asked

**Expect:** A 🔔 card: stock, condition (Price > 1100), threshold, channels
(LINE / Web Push), Edit/Dismiss controls. (Alert creation goes through ask_user
confirmation first.)

---

## 7. Supply chain — `supply_chain`

**Prompt:** `台積電 2330 的供應鏈，上下游跟競爭對手`

**Expect:** A 🔗 card with upstream (供應商) and downstream (客戶) lanes (each stock a
link), plus a competitors line.

---

## 8. Theme overview — `theme_overview`

**Prompt:** `AI 伺服器這個題材有哪些股票？分上中下游`

**Expect:** A 📊 theme card: theme name + stock count + today's %, three tier columns
(上游/中游/下游) with top stocks per tier (each a link), and today's change% colored.

---

## 9. K-line chart — `kline_chart` ⭐ NEW

**Prompt:** `畫出台積電 2330 最近一個月的 K 線圖，加上 20 日均線`

**Expect:** A candlestick chart — red/green OHLC bars, MA overlay line(s) with a
legend (e.g. MA20), volume bars below, date range at the bottom. Header shows
name/code + latest close.

---

## 10. Institutional flow — `institutional_flow_trend` ⭐ NEW

**Prompt:** `台積電 2330 最近 20 天三大法人買賣超，用圖表`

**Expect:** A grouped bar chart — 外資/投信/自營 net per day (colored series, zero
line in the middle), with a per-investor cumulative total in the legend and the date
range.

---

## 11. Financial statement — `financial_statement` ⭐ NEW

**Prompt:** `台積電 2330 最近幾季的損益表，營收、淨利、EPS、毛利率`

**Expect:** A table with periods as columns (2025Q1, 2024Q4…), metric rows on the
left, numbers right-aligned; growth/margin rows tinted green/red by sign; a unit
label (億) in the header.

---

## 12. Dividend history — `dividend_history` ⭐ NEW

**Prompt:** `台積電 2330 過去幾年的配息紀錄跟殖利率`

**Expect:** A 配息紀錄 card — a yield-trend bar strip on top, then a table: 年度 /
現金股利 / 股票股利 / 殖利率 (signal-colored) / 除息日.

---

## 13. Short position trend — `short_position_trend` ⭐ NEW

**Prompt:** `台積電 2330 的融券跟借券餘額趨勢`

**Expect:** A 借券/融券趨勢 card — two trend lines (融券餘額 red, 借券餘額 amber) over
time, with a trend arrow + latest value per series in the legend and the date range.

---

## 14. Options sentiment — `options_sentiment` ⭐ NEW

**Prompt:** `現在台指選擇權 Put/Call ratio 是多少？市場情緒如何？`

**Expect:** An options sentiment card — large Put/Call value (colored), a horizontal
greed→fear gradient gauge with a marker, sentiment label (恐懼/中性/貪婪…), and IV /
IV-rank if available.

---

## 15. ESG scorecard — `esg_scorecard` ⭐ NEW

**Prompt:** `台積電 2330 的 ESG 評分，各面向分數`

**Expect:** An ESG 評分 card — overall score /100 (colored), then per-topic bars
(公司治理 / 溫室氣體排放 / 能源管理 / 水資源 / 人力發展…) each with a score and progress bar.

---

## 16. ETF profile — `etf_profile`

**Prompt:** `0050 這檔 ETF 的基本資料，追蹤指數、規模、費用率、殖利率`

**Expect:** An ETF profile card — name/code, tracked index, AUM/scale, expense ratio,
distribution yield, and premium/discount to NAV.

---

## 17. Active ETF holders — `active_etf_holders`

**Prompt:** `主動式 ETF 00980A 的前十大持股`

**Expect:** A holdings card — the ETF's top constituents with weight %, each stock a
link to its detail page.

---

## 18. Shareholder gift — `shareholder_gift`

**Prompt:** `台積電 2330 有股東紀念品嗎？`

**Expect:** A 股東紀念品 card — gift description, the qualifying record date, and
collection details (or a clear "no gift" state if none).

---

## Troubleshooting

- **Card never renders, only text:** model didn't call the render tool. Add an
  explicit「用卡片/圖表呈現」or「畫出來」to the prompt, or rephrase to match the owning
  skill's triggers. Emission is LLM-driven and not guaranteed per turn.
- **Card renders but data looks empty / "—":** the underlying data tool returned
  nothing (non-trading day, stock has no such data, or provider 503). Try a liquid
  large-cap (2330/2454) on a trading day.
- **Wrong card type / JSON parse fail:** check the SSE `rich_card` event in the
  network tab — `card_type` must exactly match a `MessageBubble` switch case.
- **Card data shape:** every card_type → component prop shape is defined in
  `app/agent/tools/render.py` (backend args) and the component's `Props` interface
  (frontend). They must agree.
