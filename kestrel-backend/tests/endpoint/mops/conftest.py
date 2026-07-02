"""Shared fixtures for MOPS provider live tests."""

import pytest

from app.providers.mops import MOPSClient


@pytest.fixture
def client():
    return MOPSClient(request_interval=1.0)


@pytest.fixture
def tsmc():
    return "2330"


@pytest.fixture
def hon_hai():
    return "2317"
