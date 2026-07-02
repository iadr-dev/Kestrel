"""Production hardening middleware: security headers, body-size cap, timeouts.

Each is a small, independent middleware so they can be enabled/tuned via Settings
without touching business logic.
"""

import asyncio

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security response headers (HSTS, nosniff, frame/referrer)."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # HSTS only meaningful over HTTPS; harmless on plain HTTP (ignored by browsers).
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rejects requests whose Content-Length exceeds the configured maximum.

    Guards against memory-exhaustion DoS from large uploads (e.g. voice files).
    Streaming bodies without Content-Length are not pre-checked here (the ASGI
    server's own limits apply), but the common attack — a declared large body —
    is rejected before it is read.
    """

    def __init__(self, app: object, max_bytes: int) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and content_length.isdigit() and int(content_length) > self._max_bytes:
            return JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Request body exceeds {self._max_bytes} bytes",
                        "detail": {"max_bytes": self._max_bytes},
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )
        return await call_next(request)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforces a hard per-request timeout so a slow handler can't hang forever."""

    def __init__(self, app: object, timeout_seconds: float) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._timeout = timeout_seconds

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self._timeout)
        except TimeoutError:
            logger.warning("request_timeout", path=request.url.path, timeout=self._timeout)
            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "REQUEST_TIMEOUT",
                        "message": f"Request exceeded {self._timeout}s time limit",
                        "detail": {},
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
            )
