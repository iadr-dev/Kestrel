"""Shared fixtures for TDCC provider live tests."""

import pytest

from app.providers.tdcc import TDCCClient


@pytest.fixture
def client():
    return TDCCClient(request_interval=0.5)


@pytest.fixture
def tsmc():
    return "2330"


@pytest.fixture
def hon_hai():
    return "2317"
