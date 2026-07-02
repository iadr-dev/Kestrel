# Thinking-process live test

- Model: `gemini-2.5-flash`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ✅ yes
- Reasoning chars: 0 · Answer chars: 210 · Turn: 204009ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 2032 | status | thinking |
| 4589 | status | executing |
| 4589 | tool_start | analyze_stock |
| 4634 | tool_done | Unknown tool: analyze_stock |
| 4634 | status | thinking |
| 16609 | text | ×2 deltas |
| 18142 | status | executing |
| 18142 | tool_start | get_realtime_quote |
| 18592 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (97ms) |
| 18592 | status | thinking |
| 46360 | text | ×2 deltas |
| 51127 | status | executing |
| 51127 | tool_start | get_stock_price |
| 51820 | tool_done | Unknown tool: get_stock_price |
| 51820 | status | thinking |
| 136751 | text | ×2 deltas |
| 137154 | status | executing |
| 137154 | tool_start | get_indicators |
| 137611 | tool_done | Unknown tool: get_indicators |
| 137611 | status | thinking |
| 158357 | text | ×1 deltas |
| 158708 | status | executing |
| 158708 | tool_start | get_institutional_flow |
| 159412 | tool_done | Unknown tool: get_institutional_flow |
| 159412 | status | thinking |
| 182344 | text | ×1 deltas |
| 188700 | status | executing |
| 188700 | tool_start | get_twse_institutional |
| 198379 | tool_done | Unknown tool: get_twse_institutional |
| 198380 | status | thinking |
| 201595 | text | ×4 deltas |
| 202337 | status | responding |
| 204009 | follow_up |  |
| 204009 | done |  |
