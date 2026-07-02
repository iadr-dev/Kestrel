"""Shared fixtures for ETF endpoint live tests."""

import pytest


@pytest.fixture
def popular_etf():
    """0050 — most popular TW ETF (元大台灣50)."""
    return "0050"


@pytest.fixture
def bond_etf():
    """00679B — popular bond ETF."""
    return "00679B"
