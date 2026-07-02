# Thinking-process live test

- Model: `meta/llama-4-maverick-17b-128e-instruct`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ❌ no (burst)
- **Called a tool (real data):** ❌ no
- **Live tool process (start→done gap):** ❌ no
- Reasoning chars: 0 · Answer chars: 87 · Turn: 21148ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 16343 | status | thinking |
| 16645 | text | ×26 deltas |
| 17135 | status | responding |
| 21116 | follow_up |  |
| 21148 | done |  |
