"""Shared fixtures for yfinance live tests."""

import pytest

from app.providers.yfinance import YFinanceProvider


@pytest.fixture
def yf():
    """Shared YFinanceProvider instance."""
    return YFinanceProvider()


@pytest.fixture
def us_ticker():
    """High-liquidity US stock for reliable test data."""
    return "AAPL"


@pytest.fixture
def tw_ticker():
    """TSMC — most liquid TW stock, triggers .TW suffix resolution."""
    return "2330"


@pytest.fixture
def etf_ticker():
    """SPY — highly liquid ETF for fund-specific tests."""
    return "SPY"
