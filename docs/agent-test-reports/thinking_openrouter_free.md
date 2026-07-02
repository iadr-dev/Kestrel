# Thinking-process live test

- Model: `openrouter/free`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ✅ yes (1392 thinking events)
- **Incremental text stream:** ✅ yes
- **Called a tool (real data):** ❌ no
- **Live tool process (start→done gap):** ❌ no
- Reasoning chars: 5750 · Answer chars: 191 · Turn: 54629ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 26570 | status | thinking |
| 28487 | thinking | ×1392 deltas |
| 48861 | text | ×156 deltas |
| 52598 | status | responding |
| 54591 | follow_up |  |
| 54629 | done |  |
