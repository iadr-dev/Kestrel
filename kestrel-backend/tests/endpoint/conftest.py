"""Shared fixtures for live HTTP endpoint tests.

These drive the real FastAPI app end-to-end through an ASGI transport WITH the
app lifespan running, so app.state.cache / provider registry / DuckDB engine are
wired exactly as in production. Data-source API keys come from .env, and authed
endpoints use an admin (pro-tier) token so tier limits don't interfere.

The client opens the app in DUCKDB_READ_ONLY mode so startup does NOT kick off
the dev-boot ingest/seed jobs — those run a full FinMind bulk pull in a
background task that would otherwise contend with the test requests for upstream
connections (causing flaky "Server disconnected" errors). Read-only also skips
the scheduler. The existing market_data.duckdb provides the schema/data.

Run: pytest tests/endpoint/ -v
"""

import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv()

# Must be set BEFORE importing app.main / Settings so the lifespan reads them.
os.environ["DUCKDB_READ_ONLY"] = "true"
os.environ["RUN_SCHEDULER"] = "false"

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.security import create_access_token


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def live_client():
    """App-lifespan-aware async client (app.state fully initialized, no boot jobs).

    Session-scoped with a session-scoped loop (set locally via loop_scope, NOT
    globally — a global default breaks teardown of the function-scoped provider
    fixtures in the sibling finmind/twse tests). Route tests that use this client
    must also declare loop_scope="session" in their pytestmark. Opened in
    DUCKDB_READ_ONLY mode so the dev-boot ingest/seed jobs don't run and contend
    with test requests for the upstream FinMind connection.
    """
    from app.main import app
    async with LifespanManager(app, startup_timeout=120, shutdown_timeout=60) as manager:
        transport = ASGITransport(app=manager.app)
        async with AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as ac:
            yield ac


@pytest.fixture
def admin_auth():
    """Authorization header for the admin (pro-tier) account from .env."""
    settings = Settings()
    admin_email = settings.admin_emails[0] if settings.admin_emails else "admin@test.local"
    token = create_access_token(
        {"sub": "endpoint-test-admin", "email": admin_email, "tier": "pro"}, settings
    )
    return {"Authorization": f"Bearer {token}"}
