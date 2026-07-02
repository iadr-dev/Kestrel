# Thinking-process live test

- Model: `gpt-5.4-mini`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ❌ no
- Reasoning chars: 0 · Answer chars: 549 · Turn: 9010ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 2527 | status | thinking |
| 3194 | status | executing |
| 3194 | tool_start | get_realtime_quote |
| 3348 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (94ms) |
| 3348 | status | thinking |
| 4020 | text | ×394 deltas |
| 6708 | status | responding |
| 9010 | follow_up |  |
| 9010 | done |  |
