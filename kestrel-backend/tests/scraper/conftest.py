"""Shared fixtures for scraper live tests."""

import pytest


@pytest.fixture
def tsmc():
    return "2330"


@pytest.fixture
def hon_hai():
    return "2317"


@pytest.fixture
def popular_etf():
    """0050 — most popular TW ETF."""
    return "0050"
