"""In-process publish/subscribe bus for server-originated push events.

Design: producers (cron jobs, alert engine) call `publish(event, data)`; each active
SSE/WS connection holds a `Subscription` (an asyncio.Queue) it drains to the client.
Publishing is fire-and-forget and never blocks a producer — a slow/full subscriber
drops the event rather than back-pressuring the ingest.

Scope boundary (important for prod): this fans out only to subscribers ON THE SAME
PROCESS. Under multiple API workers, a client on worker A won't receive an event
published on worker B. The `Broker` interface is deliberately minimal so a
Redis-pub/sub-backed implementation can drop in later WITHOUT touching producers or
the SSE transport — that swap is the one place multi-worker push will change.
"""

import asyncio
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Bound each subscriber's queue so a stalled client can't grow memory without limit;
# on overflow we drop the oldest event (news/score pings are idempotent refresh hints,
# not a durable log, so a dropped ping just means the client refreshes on the next one).
_QUEUE_MAXSIZE = 64


class Subscription:
    """One client's event stream. Async-iterate `.events()` to receive."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)

    def _offer(self, payload: dict[str, Any]) -> None:
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            # Drop the oldest, enqueue the newest — keep the freshest refresh hint.
            try:
                self._queue.get_nowait()
                self._queue.put_nowait(payload)
            except (asyncio.QueueEmpty, asyncio.QueueFull):
                pass

    async def next(self, timeout: float) -> dict[str, Any] | None:
        """Await the next event, or None on timeout (lets the caller send a heartbeat)."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None


class _InProcessBroker:
    def __init__(self) -> None:
        self._subs: set[Subscription] = set()

    def subscribe(self) -> Subscription:
        sub = Subscription()
        self._subs.add(sub)
        return sub

    def unsubscribe(self, sub: Subscription) -> None:
        self._subs.discard(sub)

    async def publish(self, event: str, data: dict[str, Any] | None = None) -> int:
        """Fan out `event` to all current subscribers. Returns the number notified.
        Never raises into the producer."""
        payload = {"event": event, "data": data or {}}
        n = 0
        for sub in list(self._subs):
            try:
                sub._offer(payload)
                n += 1
            except Exception:
                pass
        if n:
            logger.debug("push_published", event_name=event, subscribers=n)
        return n

    @property
    def subscriber_count(self) -> int:
        return len(self._subs)


# Module-level singleton broker (swap the class here for a RedisBroker later).
_broker = _InProcessBroker()


def subscribe() -> Subscription:
    return _broker.subscribe()


def unsubscribe(sub: Subscription) -> None:
    _broker.unsubscribe(sub)


async def publish(event: str, data: dict[str, Any] | None = None) -> int:
    return await _broker.publish(event, data)


def subscriber_count() -> int:
    return _broker.subscriber_count
