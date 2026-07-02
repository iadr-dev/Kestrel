"""Server-originated push event names.

These are domain events the backend already knows about (a cron finished, an alert
fired, scores were recomputed). Producers publish them via the broker; they carry no
knowledge of who is listening or how (SSE/WS) — the transport layer handles that.
"""

# News feed advanced (ingest cron wrote fresh rows).
NEWS_UPDATED = "news_updated"

# An alert's condition was met and delivered.
ALERT_TRIGGERED = "alert_triggered"

# The daily AI scores were recomputed.
SCORES_REFRESHED = "scores_refreshed"

# All known event types (used to validate subscriptions / document the contract).
ALL_EVENTS = frozenset({NEWS_UPDATED, ALERT_TRIGGERED, SCORES_REFRESHED})
