"""Taiwan company profile fetcher.

Previously scraped the MOPS HTML site (mops/web/ajax_t05st03), which TWSE retired
when it migrated MOPS to a SPA — the old endpoint now returns a security stub.
This now reads the live TWSE/TPEx OpenAPI via the shared TWSEClient, keeping the
same return shape (stock_id, name_zh, chairman, …) so consumers are unchanged.
"""

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class MOPSProfileScraper:
    """Fetch basic company info for a Taiwan stock from the TWSE OpenAPI."""

    async def get_company_info(self, stock_id: str) -> dict[str, Any]:
        """Fetch a company profile (name, chairman, CEO, address, capital, dates)."""
        try:
            from app.providers.twse import get_twse_client
            profile = await get_twse_client().get_company_profile(stock_id)
        except Exception as e:
            logger.warning("profile_fetch_failed", stock_id=stock_id, error=str(e)[:80])
            return {"stock_id": stock_id, "error": str(e)[:80]}
        if not profile:
            return {"stock_id": stock_id, "error": "No data for company"}
        return profile
