"""Shared fixtures for TWSE/TPEx/TAIFEX live tests."""

import pytest

from app.providers.twse import TWSEClient


@pytest.fixture
def client():
    """TWSEClient with relaxed throttle for tests."""
    return TWSEClient(request_interval=0.5)


@pytest.fixture
def tsmc():
    """TSMC stock code — most liquid listed stock."""
    return "2330"


@pytest.fixture
def hon_hai():
    """Hon Hai stock code — second most liquid listed stock."""
    return "2317"


@pytest.fixture
def mediatek():
    """MediaTek stock code — third most liquid."""
    return "2454"


@pytest.fixture
def otc_stock():
    """OTC stock for TPEx tests."""
    return "6488"
