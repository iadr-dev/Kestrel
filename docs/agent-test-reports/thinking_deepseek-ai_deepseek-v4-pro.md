# Thinking-process live test

- Model: `deepseek-ai/deepseek-v4-pro`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ✅ yes
- Reasoning chars: 0 · Answer chars: 1471 · Turn: 174697ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 1459 | status | thinking |
| 2661 | text | ×3 deltas |
| 21386 | status | executing |
| 21386 | tool_start | get_realtime_quote |
| 21559 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (172ms) |
| 21559 | status | thinking |
| 27565 | text | ×5 deltas |
| 88328 | status | executing |
| 88328 | tool_start | get_indicators |
| 88328 | status | executing |
| 88328 | tool_start | get_institutional_flow |
| 88328 | status | executing |
| 88328 | tool_start | get_revenue |
| 88332 | tool_done | Unknown tool: get_indicators |
| 88332 | tool_done | Unknown tool: get_institutional_flow |
| 88332 | tool_done | Unknown tool: get_revenue |
| 88332 | status | thinking |
| 89205 | text | ×4 deltas |
| 97315 | status | executing |
| 97315 | tool_start | get_stock_price |
| 97315 | status | executing |
| 97315 | tool_start | get_twse_institutional |
| 97317 | tool_done | Unknown tool: get_stock_price |
| 97317 | tool_done | Unknown tool: get_twse_institutional |
| 97317 | status | thinking |
| 106022 | text | ×10 deltas |
| 125300 | status | executing |
| 125300 | tool_start | get_market_index |
| 125300 | status | executing |
| 125300 | tool_start | get_macro_data |
| 125301 | tool_done | Unknown tool: get_market_index |
| 125301 | tool_done | Unknown tool: get_macro_data |
| 125301 | status | thinking |
| 125967 | text | ×82 deltas |
| 172944 | status | responding |
| 174696 | follow_up |  |
| 174697 | done |  |
