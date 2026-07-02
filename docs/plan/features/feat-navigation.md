# Feature: Left Sidebar Navigation Update — ✅ DONE

## Current Nav

```
💬 Chat        /dashboard/chat
📊 Market      /dashboard/market
🔍 Screener    /dashboard/screener
💼 Portfolio   /dashboard/portfolio
⚙️ Settings    (from profile menu)
```

## Target Nav

```
🤖 AI Chat          /dashboard/chat
📊 Market           /dashboard/market
🧠 AI Analysis      /dashboard/ai-analysis    ← NEW
🔍 選股             /dashboard/screener
📈 回測             /dashboard/backtest        ← NEW (from market tab)
💼 Portfolio        /dashboard/portfolio
⚙️ Settings         /dashboard/settings
```

## Changes

| Action | Item | Reason |
|--------|------|--------|
| KEEP | AI Chat | Core feature |
| KEEP | Market | Redesigned with 2-row tabs |
| ADD | AI Analysis | New scoring/ranking page |
| KEEP | 選股 (Screener) | Standalone workflow |
| ADD | 回測 (Backtest) | Was inside market, needs own space |
| KEEP | Portfolio | Core feature |
| KEEP | Settings | Core feature |
| REMOVE | 財經創作 | Not useful at this stage |

## File to Modify

`src/components/layout/Sidebar.tsx` — Update NAV_ITEMS array, add icons, add translation keys.

## Translation Keys Needed

```json
// zh-TW
"nav": {
  "chat": "對話",
  "market": "市場",
  "ai_analysis": "AI 分析",
  "screener": "選股",
  "backtest": "回測",
  "portfolio": "持倉",
  "settings": "設定"
}
```
