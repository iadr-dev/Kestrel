"""Live HTTP-route tests for health probes and the unified error envelope.

Covers the audit additions: /health/ready readiness probe (200/503 by data
health) and the single error envelope produced for HTTPException / validation /
unknown routes by app/middleware/exception_handlers.py.

Run: pytest tests/endpoint/http/test_health_and_errors.py -v
"""

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestHealth:
    async def test_liveness(self, live_client):
        r = await live_client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    async def test_db_health(self, live_client):
        r = await live_client.get("/api/v1/health/db")
        assert r.status_code == 200
        body = r.json()
        # Real dependency checks (DuckDB / SQLAlchemy / cache).
        assert "duckdb" in body
        assert "sqlalchemy" in body
        assert "cache" in body

    async def test_readiness(self, live_client):
        """Readiness returns 200 ready / 503 not_ready with a checks breakdown."""
        r = await live_client.get("/api/v1/health/ready")
        assert r.status_code in (200, 503)
        body = r.json()
        assert body["status"] in ("ready", "not_ready")
        assert "checks" in body


class TestErrorEnvelope:
    async def test_unknown_route_404_envelope(self, live_client):
        """Unknown route → 404 in the unified {"error": {...}} envelope."""
        r = await live_client.get("/api/v1/stocks/this-route-does-not-exist-xyz")
        assert r.status_code == 404
        body = r.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    async def test_validation_error_envelope(self, live_client):
        """A bad query param surfaces the VALIDATION_ERROR envelope, not FastAPI's default."""
        r = await live_client.get("/api/v1/stocks/2330/price")  # missing required start_date
        assert r.status_code == 422
        body = r.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "detail" in body["error"]
