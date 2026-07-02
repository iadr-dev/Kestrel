"""TWSE OpenAPI methods."""

from typing import TYPE_CHECKING, Any

from app.providers.twse.client import TWSE_BASE_URL

if TYPE_CHECKING:
    from app.providers.twse.client import TWSEClient


async def fetch_openapi(self: "TWSEClient", endpoint: str) -> list[dict[str, Any]]:
    """Fetch from TWSE OpenAPI (relative endpoint)."""
    url = f"{TWSE_BASE_URL}{endpoint}"
    data = await self._get(url)
    return data if isinstance(data, list) else ([data] if data else [])


async def fetch_company(self: "TWSEClient", endpoint: str, code: str) -> dict[str, Any] | None:
    """Fetch single company data by code."""
    data = await self.fetch_openapi(endpoint)
    for item in data:
        if isinstance(item, dict):
            if item.get("公司代號") == code or item.get("Code") == code or item.get("權證代號") == code:
                return item
    return None


# Listed-company basic profile (Chinese keys, t187ap03_L) and OTC profile
# (English keys, mopsfin_t187ap03_O) → one normalized shape. This replaces the
# dead MOPS HTML scraper (mops/web/t05st03), which stopped returning data after
# TWSE migrated the site. Both OpenAPI feeds are JSON and refreshed daily.
def _norm_listed(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a TWSE listed-company row (Chinese keys) to a profile dict."""
    return {
        "name_zh": row.get("公司名稱"),
        "name_en": row.get("英文簡稱"),
        "chairman": row.get("董事長"),
        "ceo": row.get("總經理"),
        "spokesman": row.get("發言人"),
        "spokesman_title": row.get("發言人職稱"),
        "headquarters": row.get("住址"),
        "phone": row.get("總機電話"),
        "founded_date": _fmt_ymd(row.get("成立日期")),
        "listed_date": _fmt_ymd(row.get("上市日期")),
        "capital": row.get("實收資本額"),
        "website": (row.get("網址") or "").strip() or None,
        "email": row.get("電子郵件信箱"),
        "industry_code": row.get("產業別"),
    }


def _norm_otc(row: dict[str, Any]) -> dict[str, Any]:
    """Normalize a TPEx OTC-company row (English keys) to a profile dict."""
    return {
        "name_zh": row.get("CompanyName"),
        "name_en": (row.get("Symbol") or "").strip() or None,
        "chairman": row.get("Chairman"),
        "ceo": row.get("GeneralManager"),
        "spokesman": row.get("Spokesman"),
        "spokesman_title": row.get("TitleOfSpokesman"),
        "headquarters": row.get("Address"),
        "phone": row.get("Telephone"),
        "founded_date": _fmt_ymd(row.get("DateOfIncorporation")),
        "listed_date": _fmt_ymd(row.get("DateOfListing")),
        "capital": row.get("Paidin.Capital.NTDollars"),
        "website": (row.get("WebAddress") or "").strip() or None,
        "email": row.get("EmailAddress"),
        "industry_code": row.get("SecuritiesIndustryCode"),
    }


def _fmt_ymd(value: str | None) -> str | None:
    """Format an 8-digit AD date string (19501229) as 1950-12-29."""
    if not value or not value.isdigit() or len(value) != 8:
        return value or None
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}"


async def get_company_profile(self: "TWSEClient", code: str) -> dict[str, Any] | None:
    """Company basic profile (chairman, CEO, spokesman, address, capital, dates,
    website) for a TW stock. Tries the listed-company feed first, then OTC.

    Returns a normalized dict with empty fields dropped, or None if the code is
    not found in either feed. Replaces the retired MOPS scraper."""
    listed = await self.fetch_company("/opendata/t187ap03_L", code)
    if listed:
        profile = _norm_listed(listed)
    else:
        otc_rows = await self.fetch_tpex("mopsfin_t187ap03_O")
        match = next((r for r in otc_rows if r.get("SecuritiesCompanyCode") == code), None)
        if not match:
            return None
        profile = _norm_otc(match)
    profile["stock_id"] = code
    profile["market"] = "TW"
    return {k: v for k, v in profile.items() if v not in (None, "")}
