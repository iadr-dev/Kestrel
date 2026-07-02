"""Test configuration — shared fixtures for live API tests."""

import asyncio
import time

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def rate_limit_delay():
    """Sleep between tests to avoid rate limiting from TWSE/TPEx/TAIFEX."""
    yield
    time.sleep(1.0)


@pytest.fixture
def sample_stock_code():
    """TSMC — most liquid TW stock."""
    return "2330"


@pytest.fixture
def sample_otc_code():
    """OTC stock for testing."""
    return "6488"
