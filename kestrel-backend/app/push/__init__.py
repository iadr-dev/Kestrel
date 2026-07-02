"""Server push layer — decoupled domain events + pub/sub broker + SSE transport.

Producers: `from app.push import broker, events; await broker.publish(events.NEWS_UPDATED)`
Transport: app.push.sse.router (mounted in the API router).

Separation of concerns (see broker.py): producers don't know consumers; the broker
is swappable (in-process now, Redis later for multi-worker) without touching either
producers or the SSE transport.
"""

from app.push import broker, events

__all__ = ["broker", "events"]
