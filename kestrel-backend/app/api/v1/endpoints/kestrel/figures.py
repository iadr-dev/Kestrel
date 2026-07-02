"""Figure Events endpoints — track high-profile figures and their stock market impact."""

import json
from typing import Any

from fastapi import APIRouter, Query

from app.db.duckdb.engine import get_duckdb
from app.schemas.figures import (
    FigureCategoriesResponse,
    FigureEventsResponse,
    FigureListResponse,
    FigureTimelineResponse,
)

router = APIRouter(prefix="/figures", tags=["Figure Events"])


@router.get("", response_model=FigureListResponse)
async def get_figures(
    category: str | None = Query(None, description="Filter by: tech_ceo, politician, central_bank, investor, taiwan"),
) -> dict[str, Any]:
    """Get all tracked figures, optionally filtered by category."""
    db = get_duckdb()

    if category:
        rows = await db.aquery(
            "SELECT * FROM figures WHERE category = ? ORDER BY name_en",
            [category],
        )
    else:
        rows = await db.aquery("SELECT * FROM figures ORDER BY category, name_en")

    columns = ["id", "name_en", "name_zh", "role", "category", "photo_url", "associated_stocks"]
    data = []
    for row in rows:
        item = dict(zip(columns, row, strict=False))
        item["associated_stocks"] = json.loads(item["associated_stocks"]) if item["associated_stocks"] else []
        data.append(item)

    return {"data": data, "count": len(data)}


@router.get("/events", response_model=FigureEventsResponse)
async def get_events(
    figure_id: str | None = Query(None),
    stock_id: str | None = Query(None),
    event_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Get figure events with optional filtering."""
    db = get_duckdb()

    conditions = []
    params: list[Any] = []

    if figure_id:
        conditions.append("fe.figure_id = ?")
        params.append(figure_id)
    if stock_id:
        conditions.append("(fe.primary_stock_id = ? OR fe.affected_stocks::VARCHAR LIKE '%' || ? || '%')")
        params.extend([stock_id, stock_id])
    if event_type:
        conditions.append("fe.event_type = ?")
        params.append(event_type)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sql = f"""
        SELECT
            fe.id, fe.figure_id, fe.event_date, fe.event_type, fe.title,
            fe.description, fe.source_url, fe.primary_stock_id, fe.affected_stocks,
            fe.impact_1d, fe.impact_5d, fe.impact_30d, fe.sentiment, fe.importance,
            f.name_en AS figure_name_en, f.name_zh AS figure_name_zh,
            f.category AS figure_category, f.photo_url AS figure_photo
        FROM figure_events fe
        JOIN figures f ON fe.figure_id = f.id
        {where_clause}
        ORDER BY fe.event_date DESC
        LIMIT ?
    """
    params.append(limit)

    rows = await db.aquery(sql, params)
    columns = [
        "id", "figure_id", "event_date", "event_type", "title",
        "description", "source_url", "primary_stock_id", "affected_stocks",
        "impact_1d", "impact_5d", "impact_30d", "sentiment", "importance",
        "figure_name_en", "figure_name_zh", "figure_category", "figure_photo",
    ]

    data = []
    for row in rows:
        item = dict(zip(columns, row, strict=False))
        item["affected_stocks"] = json.loads(item["affected_stocks"]) if item["affected_stocks"] else []
        item["event_date"] = str(item["event_date"])
        data.append(item)

    return {"data": data, "count": len(data)}


@router.get("/timeline/{figure_id}", response_model=FigureTimelineResponse)
async def get_figure_timeline(
    figure_id: str,
    limit: int = Query(30, ge=1, le=100),
) -> dict[str, Any]:
    """Get a specific figure's profile + event timeline."""
    db = get_duckdb()

    fig_row = await db.aquery_one("SELECT * FROM figures WHERE id = ?", [figure_id])
    if not fig_row:
        return {"figure": None, "events": []}

    fig_cols = ["id", "name_en", "name_zh", "role", "category", "photo_url", "associated_stocks"]
    figure = dict(zip(fig_cols, fig_row, strict=False))
    figure["associated_stocks"] = json.loads(figure["associated_stocks"]) if figure["associated_stocks"] else []

    events_rows = await db.aquery("""
        SELECT id, event_date, event_type, title, description, source_url,
               primary_stock_id, affected_stocks, impact_1d, impact_5d, impact_30d,
               sentiment, importance
        FROM figure_events
        WHERE figure_id = ?
        ORDER BY event_date DESC
        LIMIT ?
    """, [figure_id, limit])

    evt_cols = [
        "id", "event_date", "event_type", "title", "description", "source_url",
        "primary_stock_id", "affected_stocks", "impact_1d", "impact_5d", "impact_30d",
        "sentiment", "importance",
    ]
    events = []
    for row in events_rows:
        item = dict(zip(evt_cols, row, strict=False))
        item["affected_stocks"] = json.loads(item["affected_stocks"]) if item["affected_stocks"] else []
        item["event_date"] = str(item["event_date"])
        events.append(item)

    return {"figure": figure, "events": events}


@router.get("/categories", response_model=FigureCategoriesResponse)
async def get_categories() -> dict[str, Any]:
    """Get available figure categories with counts."""
    db = get_duckdb()

    rows = await db.aquery("""
        SELECT category, COUNT(*) as count
        FROM figures
        GROUP BY category
        ORDER BY count DESC
    """)

    return {"data": [{"category": r[0], "count": r[1]} for r in rows]}
