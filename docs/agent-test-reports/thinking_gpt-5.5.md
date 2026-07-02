# Thinking-process live test

- Model: `gpt-5.5`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ✅ yes
- Reasoning chars: 0 · Answer chars: 910 · Turn: 26094ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 2887 | status | thinking |
| 6766 | status | executing |
| 6766 | tool_start | get_realtime_quote |
| 6969 | tool_done | 台積電(2330): $2505.0000 ▲95.00 (+3.94%) | 量:30361張 | 高:2505.0000 低:2475.0000 (147ms) |
| 6969 | status | thinking |
| 14687 | text | ×639 deltas |
| 23923 | status | responding |
| 26093 | follow_up |  |
| 26094 | done |  |
