"""MIS real-time quote methods."""

import time
from typing import TYPE_CHECKING, Any

from app.providers.twse.client import MIS_URL

if TYPE_CHECKING:
    from app.providers.twse.client import TWSEClient


async def get_realtime_quote(self: "TWSEClient", stock_nos: list[str]) -> list[dict[str, Any]]:
    """Get real-time quotes for multiple stocks."""
    ex_codes = []
    for code in stock_nos:
        ex_codes.append(f"tse_{code}.tw")
    codes_str = "|".join(ex_codes)
    url = f"{MIS_URL}/getStockInfo.jsp"
    raw = await self._get(url, params={"ex_ch": codes_str, "json": "1", "_": str(int(time.time() * 1000))})
    msg_array = raw.get("msgArray", [])
    if not msg_array:
        otc_codes = [f"otc_{c.split('.')[0].replace('tse_', '')}.tw" for c in ex_codes]
        codes_str = "|".join(otc_codes)
        raw = await self._get(url, params={"ex_ch": codes_str, "json": "1", "_": str(int(time.time() * 1000))})
        msg_array = raw.get("msgArray", [])
    return list(msg_array)
