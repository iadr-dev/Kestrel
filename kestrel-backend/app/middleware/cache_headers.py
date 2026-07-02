"""HTTP Cache-Control header middleware — enables browser-side caching."""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CacheHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        path = request.url.path

        # Skip caching for mutations and auth
        if request.method != "GET":
            return response
        if "/auth/" in path or "/agent/" in path or "/user/" in path:
            return response

        # Market data: 5 min cache
        if "/market/" in path or "/stocks/" in path:
            response.headers["Cache-Control"] = "public, max-age=300"
        # Macro data: 1 hour (changes slowly)
        elif "/macro/" in path:
            response.headers["Cache-Control"] = "public, max-age=3600"
        # Institutional data: 15 min
        elif "/institutional/" in path:
            response.headers["Cache-Control"] = "public, max-age=900"
        # Fundamentals: 1 hour
        elif "/fundamentals/" in path:
            response.headers["Cache-Control"] = "public, max-age=3600"
        # Derivatives: 5 min
        elif "/derivatives/" in path or "/international/" in path or "/screener/" in path:
            response.headers["Cache-Control"] = "public, max-age=300"
        # Observe: no cache (admin real-time data)
        elif "/observe/" in path:
            response.headers["Cache-Control"] = "no-cache"

        return response
