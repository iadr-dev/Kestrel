# Thinking-process live test

- Model: `gemini-3.5-flash`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ❌ no (burst)
- **Called a tool (real data):** ✅ yes
- **Live tool process (start→done gap):** ❌ no
- Reasoning chars: 0 · Answer chars: 0 · Turn: 24941ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 21184 | status | thinking |
| 24939 | status | executing |
| 24939 | tool_start | get_realtime_quote |
| 24940 | status | responding |
| 24941 | done |  |
