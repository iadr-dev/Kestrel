# Thinking-process live test

- Model: `deepseek-ai/deepseek-v4-flash`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ✅ yes
- Reasoning chars: 0 · Answer chars: 1219 · Turn: 168892ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 17432 | status | thinking |
| 39143 | text | ×2 deltas |
| 39769 | status | executing |
| 39769 | tool_start | get_realtime_quote |
| 40800 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (226ms) |
| 40800 | status | thinking |
| 87706 | text | ×2 deltas |
| 88601 | status | executing |
| 88601 | tool_start | get_stock_price |
| 89182 | tool_done | Unknown tool: get_stock_price |
| 89182 | status | thinking |
| 109133 | text | ×1 deltas |
| 109463 | status | executing |
| 109463 | tool_start | stock_analysis |
| 110453 | tool_done | Unknown tool: stock_analysis |
| 110453 | status | thinking |
| 133603 | text | ×67 deltas |
| 166266 | status | responding |
| 168891 | follow_up |  |
| 168892 | done |  |
