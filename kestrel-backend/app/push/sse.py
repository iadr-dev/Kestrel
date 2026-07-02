"""SSE transport for server-originated push events.

GET /events/stream — any frontend (web EventSource, mobile, desktop) subscribes here
to receive news/alert/score refresh hints without polling. This is only the delivery
layer: it drains a broker Subscription and writes SSE frames. Swapping the broker
(in-process → Redis) needs no change here.
"""

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.logging import get_logger
from app.push import broker

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["Push"])

_SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
_HEARTBEAT_SECS = 25.0  # keep the connection alive through proxies when idle


@router.get("/stream")
async def events_stream(request: Request) -> StreamingResponse:
    """Subscribe to the server push bus. Emits `event: <name>` SSE frames plus a
    periodic `: ping` comment as a heartbeat. The stream ends when the client
    disconnects."""
    sub = broker.subscribe()

    async def gen() -> AsyncGenerator[str, None]:
        # Initial comment so the client's onopen fires immediately.
        yield ": connected\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                payload = await sub.next(timeout=_HEARTBEAT_SECS)
                if payload is None:
                    yield ": ping\n\n"  # heartbeat
                    continue
                yield f"event: {payload['event']}\ndata: {json.dumps(payload['data'], ensure_ascii=False)}\n\n"
        finally:
            broker.unsubscribe(sub)

    return StreamingResponse(gen(), media_type="text/event-stream", headers=_SSE_HEADERS)
