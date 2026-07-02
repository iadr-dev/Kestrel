# Thinking-process live test

- Model: `gpt-5.4`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ✅ yes
- Reasoning chars: 0 · Answer chars: 762 · Turn: 13604ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 2609 | status | thinking |
| 3896 | status | executing |
| 3896 | tool_start | get_realtime_quote |
| 4224 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (259ms) |
| 4224 | status | thinking |
| 5376 | text | ×544 deltas |
| 11623 | status | responding |
| 13604 | follow_up |  |
| 13604 | done |  |
