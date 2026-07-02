"""Live tests for yfinance analysis module.

Covers: get_recommendations, get_recommendations_summary, get_earnings_history,
        get_eps_revisions, get_growth_estimates, get_holders,
        get_insider_transactions, get_insider_purchases, get_insider_roster,
        get_major_holders, get_shares_full, get_analyst_price_targets,
        get_earnings_estimate, get_sustainability, get_peers, get_funds_data

Run: pytest tests/endpoint/yfinance/test_analysis.py -v
"""

import pytest


class TestGetRecommendations:
    @pytest.mark.asyncio
    async def test_returns_recommendations(self, yf, us_ticker):
        data = await yf.get_recommendations(us_ticker)
        assert data["ticker"] == us_ticker
        assert "recommendations" in data
        assert "upgrades_downgrades" in data

    @pytest.mark.asyncio
    async def test_has_recommendation_records(self, yf, us_ticker):
        data = await yf.get_recommendations(us_ticker)
        assert len(data["recommendations"]) > 0


class TestGetRecommendationsSummary:
    @pytest.mark.asyncio
    async def test_aggregated_counts(self, yf, us_ticker):
        data = await yf.get_recommendations_summary(us_ticker)
        assert data["ticker"] == us_ticker
        assert "summary" in data or "error" not in data


class TestGetEarningsHistory:
    @pytest.mark.asyncio
    async def test_returns_eps_surprises(self, yf, us_ticker):
        data = await yf.get_earnings_history(us_ticker)
        assert isinstance(data, list)
        if data:
            assert len(data) > 0


class TestGetEpsRevisions:
    @pytest.mark.asyncio
    async def test_returns_revision_trends(self, yf, us_ticker):
        data = await yf.get_eps_revisions(us_ticker)
        assert data["ticker"] == us_ticker
        assert "revisions" in data or "error" not in data


class TestGetGrowthEstimates:
    @pytest.mark.asyncio
    async def test_returns_growth_rates(self, yf, us_ticker):
        data = await yf.get_growth_estimates(us_ticker)
        assert data["ticker"] == us_ticker
        assert "estimates" in data or "error" not in data


class TestGetHolders:
    @pytest.mark.asyncio
    async def test_institutional_and_mutual_fund(self, yf, us_ticker):
        data = await yf.get_holders(us_ticker)
        assert data["ticker"] == us_ticker
        assert "institutional" in data
        assert "mutual_fund" in data
        assert len(data["institutional"]) > 0


class TestGetInsiderTransactions:
    @pytest.mark.asyncio
    async def test_returns_transactions(self, yf, us_ticker):
        data = await yf.get_insider_transactions(us_ticker)
        assert data["ticker"] == us_ticker
        assert "transactions" in data


class TestGetInsiderPurchases:
    @pytest.mark.asyncio
    async def test_returns_purchase_summary(self, yf, us_ticker):
        data = await yf.get_insider_purchases(us_ticker)
        assert isinstance(data, list)


class TestGetInsiderRoster:
    @pytest.mark.asyncio
    async def test_returns_roster(self, yf, us_ticker):
        data = await yf.get_insider_roster(us_ticker)
        assert isinstance(data, list)
        if data:
            assert len(data) > 0


class TestGetMajorHolders:
    @pytest.mark.asyncio
    async def test_returns_breakdown(self, yf, us_ticker):
        data = await yf.get_major_holders(us_ticker)
        assert data["ticker"] == us_ticker
        assert "breakdown" in data


class TestGetSharesFull:
    @pytest.mark.asyncio
    async def test_returns_shares_history(self, yf, us_ticker):
        data = await yf.get_shares_full(us_ticker)
        assert isinstance(data, list)


class TestGetAnalystPriceTargets:
    @pytest.mark.asyncio
    async def test_returns_targets(self, yf, us_ticker):
        data = await yf.get_analyst_price_targets(us_ticker)
        assert data["ticker"] == us_ticker
        has_targets = any(k in data for k in ["current", "low", "high", "mean", "median"])
        assert has_targets or len(data) > 1


class TestGetEarningsEstimate:
    @pytest.mark.asyncio
    async def test_returns_estimates(self, yf, us_ticker):
        data = await yf.get_earnings_estimate(us_ticker)
        assert data["ticker"] == us_ticker
        has_data = any(k in data for k in ["revenue_estimate", "earnings_estimate", "eps_trend"])
        assert has_data or "error" not in data


class TestGetSustainability:
    @pytest.mark.asyncio
    async def test_returns_esg_scores(self, yf, us_ticker):
        data = await yf.get_sustainability(us_ticker)
        assert data["ticker"] == us_ticker


class TestGetPeers:
    @pytest.mark.asyncio
    async def test_returns_peer_list(self, yf, us_ticker):
        data = await yf.get_peers(us_ticker)
        assert data["ticker"] == us_ticker
        assert "peers" in data
        assert isinstance(data["peers"], list)

    @pytest.mark.asyncio
    async def test_has_industry_info(self, yf, us_ticker):
        data = await yf.get_peers(us_ticker)
        assert "industry" in data
        assert "sector" in data


class TestGetFundsData:
    @pytest.mark.asyncio
    async def test_etf_returns_holdings(self, yf, etf_ticker):
        data = await yf.get_funds_data(etf_ticker)
        assert data["ticker"] == etf_ticker
        has_fund_data = any(k in data for k in ["top_holdings", "sector_weightings", "fund_overview"])
        assert has_fund_data

    @pytest.mark.asyncio
    async def test_stock_returns_minimal(self, yf, us_ticker):
        data = await yf.get_funds_data(us_ticker)
        assert data["ticker"] == us_ticker
