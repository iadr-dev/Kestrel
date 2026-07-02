# Thinking-process live test

- Model: `gemini-3.1-pro-preview`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ❌ no (burst)
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ❌ no
- Reasoning chars: 0 · Answer chars: 0 · Turn: 6669ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 1756 | status | thinking |
| 6659 | status | executing |
| 6659 | tool_start | get_realtime_quote |
| 6668 | status | responding |
| 6669 | done |  |
