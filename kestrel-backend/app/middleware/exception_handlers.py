"""Centralized FastAPI exception handlers — one error envelope for everything.

Every error response (custom KestrelError, raw HTTPException, request-validation
failure, or an unhandled exception) is rendered as the SAME shape so clients only
ever parse one format:

    {"error": {"code": "...", "message": "...", "detail": {...}, "request_id": "..."}}

Before this, raw `HTTPException` bypassed the KestrelError envelope and returned
FastAPI's default `{"detail": "..."}`, so clients saw two incompatible formats.
These handlers normalize all of them.
"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import KestrelError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Map common HTTP status codes to stable, machine-readable error codes so clients
# can branch on `error.code` instead of brittle string matching.
_STATUS_TO_CODE = {
    400: "BAD_REQUEST",
    401: "AUTHENTICATION_REQUIRED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    502: "PROVIDER_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


def _envelope(
    status_code: int,
    code: str,
    message: str,
    request: Request,
    detail: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "detail": detail if detail is not None else {},
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers that render the unified error envelope."""

    @app.exception_handler(KestrelError)
    async def _kestrel(request: Request, exc: KestrelError) -> JSONResponse:
        return _envelope(exc.status_code, exc.error_code, exc.message, request, exc.detail)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # FastAPI's HTTPException is a subclass of Starlette's, so this catches both.
        code = _STATUS_TO_CODE.get(exc.status_code, f"HTTP_{exc.status_code}")
        # exc.detail is usually a string; pass non-string detail through as structured.
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        detail = None if isinstance(exc.detail, str) else exc.detail
        return _envelope(exc.status_code, code, message, request, detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _envelope(
            422,
            "VALIDATION_ERROR",
            "Request validation failed",
            request,
            {"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error=str(exc), path=request.url.path)
        return _envelope(500, "INTERNAL_ERROR", "An unexpected error occurred", request)
