"""Live tests for FinMind provider health and tier validation.

Run: pytest tests/endpoint/finmind/test_health.py -v
"""

import pytest

from app.core.constants import FinMindDataset


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_reports_healthy(self, provider):
        health = await provider.health_check()
        assert health["status"] == "healthy"
        assert health["provider"] == "finmind"

    @pytest.mark.asyncio
    async def test_reports_sponsor_tier(self, provider):
        health = await provider.health_check()
        assert health["tier"] == "sponsor"

    @pytest.mark.asyncio
    async def test_rate_limit_info(self, provider):
        health = await provider.health_check()
        assert health["rate_limit_max"] == 600
        assert health["rate_limit_remaining"] > 0


class TestTierValidation:
    @pytest.mark.asyncio
    async def test_supports_free_dataset(self, provider):
        assert await provider.supports_dataset(FinMindDataset.TAIWAN_STOCK_PRICE)

    @pytest.mark.asyncio
    async def test_supports_backer_dataset(self, provider):
        assert await provider.supports_dataset(FinMindDataset.TAIWAN_STOCK_PRICE_TICK)

    @pytest.mark.asyncio
    async def test_supports_sponsor_dataset(self, provider):
        assert await provider.supports_dataset(FinMindDataset.TAIWAN_STOCK_INFO_WITH_WARRANT_SUMMARY)

    @pytest.mark.asyncio
    async def test_rejects_unknown_dataset(self, provider):
        assert not await provider.supports_dataset("NonExistentDataset")
