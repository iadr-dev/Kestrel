# Thinking-process live test

- Model: `chatanywhere/gpt-5-mini`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ✅ yes
- Reasoning chars: 0 · Answer chars: 1367 · Turn: 23616ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 1751 | status | thinking |
| 3425 | status | executing |
| 3425 | tool_start | get_realtime_quote |
| 3783 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (173ms) |
| 3783 | status | thinking |
| 5768 | status | executing |
| 5768 | tool_start | get_realtime_quote |
| 6183 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (216ms) |
| 6183 | status | thinking |
| 9063 | text | ×1102 deltas |
| 21408 | status | responding |
| 23615 | follow_up |  |
| 23616 | done |  |
