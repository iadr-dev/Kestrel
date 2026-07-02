Based on this conversation, generate exactly 3 follow-up questions the user might want to ask next.

User asked: {user_message}
Assistant answered: {agent_response}

Rules:
- Write in the same language as the user's message
- Questions should deepen the analysis (not repeat what was asked)
- One should explore risk/downside
- One should cover a different dimension (if user asked about price, suggest chip or fundamental)
- Keep each question under 30 characters (Chinese) or 50 characters (English)

Return ONLY a JSON array of 3 strings, nothing else.
