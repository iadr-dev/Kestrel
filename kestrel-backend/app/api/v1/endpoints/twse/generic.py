"""Generic TWSE OpenAPI passthrough — covers all 143 endpoints via path parameter."""

from typing import Any

from fastapi import APIRouter, Query

from app.providers.twse import get_twse_client
from app.schemas.common import DataListResponse

router = APIRouter(tags=["TWSE Generic"])


@router.get("/openapi/{endpoint:path}", response_model=DataListResponse)
async def twse_openapi_passthrough(
    endpoint: str,
    code: str | None = Query(None, description="Filter by company code"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Generic passthrough to any TWSE OpenAPI endpoint.

    Covers all 143 TWSE OpenAPI tools without needing individual route handlers.

    Examples:
    - /twse/openapi/opendata/t187ap03_L?code=2330 → company profile
    - /twse/openapi/opendata/t187ap46_L_1?code=2330 → ESG greenhouse gas
    - /twse/openapi/opendata/t187ap46_L_2?code=2330 → ESG energy management
    - /twse/openapi/opendata/t187ap37_L → all warrants
    - /twse/openapi/opendata/t187ap18 → broker list
    - /twse/openapi/opendata/t187ap08_L → board insufficient shares
    - /twse/openapi/opendata/t187ap24_L → ownership changes
    - /twse/openapi/opendata/t187ap34_L → cumulative voting
    - /twse/openapi/opendata/t187ap38_L → shareholder meeting announcements
    - /twse/openapi/opendata/t187ap29_A_L?code=2330 → director compensation
    - /twse/openapi/opendata/t187ap29_B_L?code=2330 → supervisor compensation
    """
    client = get_twse_client()
    if code:
        data = await client.fetch_company(f"/{endpoint}", code)
        return {"data": data}
    else:
        all_data = await client.fetch_openapi(f"/{endpoint}")
        paginated = all_data[offset:offset + limit]
        return {"data": paginated, "count": len(paginated), "total": len(all_data)}
