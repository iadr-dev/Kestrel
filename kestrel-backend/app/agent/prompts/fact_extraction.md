Analyze this user message and extract structured facts about the user.

User said: "{user_message}"
Agent responded about: "{response_summary}"

Extract ONLY clear, confident facts. Return a JSON array of objects:
[
  {"type": "preference|history|pattern|goal|portfolio", "key": "short key", "value": "fact value", "confidence": 0.0-1.0}
]

Examples:
- User asks about 2330 repeatedly -> {"type": "portfolio", "key": "watches_2330", "value": "actively monitors TSMC", "confidence": 0.9}
- User says "I prefer technical analysis" -> {"type": "preference", "key": "analysis_style", "value": "technical analysis focused", "confidence": 0.95}
- User asks about dividends -> {"type": "goal", "key": "income_investing", "value": "interested in dividend income", "confidence": 0.7}

If no clear facts can be extracted, return an empty array: []
Return ONLY valid JSON, nothing else.
