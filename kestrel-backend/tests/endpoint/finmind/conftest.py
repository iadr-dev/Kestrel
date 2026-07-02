"""Shared fixtures for FinMind live tests.

Requires FINMIND_API_KEY in .env (sponsor tier).
"""

from datetime import date, timedelta

import pytest

from app.core.config import Settings
from app.providers.finmind.provider import FinMindProvider


@pytest.fixture
async def provider():
    """Initialized FinMind provider (sponsor tier)."""
    settings = Settings()
    p = FinMindProvider(settings)
    await p.initialize()
    yield p
    await p.close()


@pytest.fixture
def tw_stock():
    """TSMC — most liquid stock."""
    return "2330"


@pytest.fixture
def tw_stock_2():
    """Hon Hai — second most traded."""
    return "2317"


@pytest.fixture
def otc_stock():
    """OTC stock for testing."""
    return "6488"


@pytest.fixture
def recent_start():
    """10 days ago — avoids weekends/holidays."""
    return date.today() - timedelta(days=10)


@pytest.fixture
def month_start():
    """30 days ago — for weekly/monthly datasets."""
    return date.today() - timedelta(days=30)


@pytest.fixture
def quarter_start():
    """90 days ago — for revenue/financial statements."""
    return date.today() - timedelta(days=90)


@pytest.fixture
def year_start():
    """365 days ago — for annual data."""
    return date.today() - timedelta(days=365)
