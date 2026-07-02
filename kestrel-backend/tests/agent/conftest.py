"""Agent test configuration — handles event loop lifecycle for shared clients."""

import pytest
from dotenv import load_dotenv

load_dotenv()


@pytest.fixture(autouse=True)
async def _cleanup_clients():
    """Ensure provider singleton clients are closed after each test."""
    yield
    # Close any open singleton clients to avoid event loop closed errors
    import app.providers.mops.client as mops_mod
    import app.providers.tdcc.client as tdcc_mod
    import app.providers.twse.client as twse_mod

    if twse_mod._twse_client:
        await twse_mod._twse_client.close()
        twse_mod._twse_client = None
    if tdcc_mod._tdcc_client:
        await tdcc_mod._tdcc_client.close()
        tdcc_mod._tdcc_client = None
    if mops_mod._mops_client:
        await mops_mod._mops_client.close()
        mops_mod._mops_client = None
