"""MOPS (公開資訊觀測站) provider package."""

from app.providers.mops.client import MOPSClient, get_mops_client

__all__ = ["MOPSClient", "get_mops_client"]
