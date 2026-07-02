"""TDCC (Taiwan Depository & Clearing Corporation) provider package."""

from app.providers.tdcc.client import TDCCClient, get_tdcc_client

__all__ = ["TDCCClient", "get_tdcc_client"]
