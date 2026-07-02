Analyze these news headlines and identify any that involve these high-profile figures:
{figure_names}

News:
{news_text}

For each relevant news item, extract:
- figure_name: the person's English name
- event_type: one of [speech, trade, policy, product, legal, visit, filing]
- title: concise event title (under 100 chars)
- description: 1-2 sentence description
- primary_stock_id: most affected stock ticker
- affected_stocks: array of affected tickers
- sentiment: positive, negative, or neutral
- importance: 1-10 scale

Return JSON array. If no relevant events found, return [].
Only include events where the figure is a PRIMARY actor, not just mentioned.
