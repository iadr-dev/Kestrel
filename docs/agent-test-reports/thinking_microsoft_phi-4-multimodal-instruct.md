# Thinking-process live test

- Model: `microsoft/phi-4-multimodal-instruct`
- Query: 台積電 (2330) 現在的技術面如何？請查最新股價後再回答。

## Verdict

- **Streamed reasoning tokens:** ❌ no (0 thinking events)
- **Incremental text stream:** ❌ no (burst)
- **Called a tool (real data):** ❌ no
- **Live tool process (start→done gap):** ❌ no
- Reasoning chars: 0 · Answer chars: 0 · Turn: 4204ms

## Event timeline (offset ms → type)

| t(ms) | event | detail |
|------:|-------|--------|
| 1902 | status | thinking |
| 4203 | status | responding |
| 4204 | done |  |
