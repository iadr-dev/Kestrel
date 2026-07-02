A tool call failed. Decide how to handle the error.

Tool: {tool_name}
Error: {error_message}
User's original question: {user_question}

Recovery strategies:
1. Retry with different parameters (if the error suggests bad input)
2. Use an alternative tool that provides similar data
3. Proceed with partial data and acknowledge the gap to the user
4. Ask the user for clarification if the error is due to ambiguous input

Alternative tool mappings:
- get_stock_price failed → try get_realtime_quote
- get_institutional_flow failed → try get_twse_institutional
- get_revenue failed → try get_financials
- web_search failed → try fetch_page with a specific URL
- get_realtime_quote failed (after hours) → use get_stock_price for last close

Choose ONE strategy and execute it. Do not give up on the first failure.
