from datetime import date
from typing import Any, Generic, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel, Field

T = TypeVar("T")


def ensure_valid_range(start_date: date | None, end_date: date | None) -> None:
    """Reject an inverted date range (end < start) with a 422, instead of letting
    it silently return an empty result set downstream.

    Shared one-liner guard for the market-data range endpoints. Purely additive:
    valid ranges (everything the app itself sends — start = daysAgo(n), end = today)
    are unaffected; only genuinely bad/external input is rejected. Handles optional
    bounds (no-op when either side is None)."""
    if start_date is not None and end_date is not None and end_date < start_date:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    total: int
    page: int = 1
    page_size: int = 100


class DataListResponse(BaseModel):
    """Generic list data response — used by most market data endpoints."""
    model_config = {"extra": "allow"}

    data: list[Any] = Field(default_factory=list)
    count: int = 0


class DataResponse(BaseModel):
    """Generic single-item data response."""
    model_config = {"extra": "allow"}

    data: Any = None


class DataListWithMeta(BaseModel):
    """List response with extra metadata fields."""
    data: list[Any] = Field(default_factory=list)
    count: int = 0
    summary: dict[str, Any] | None = None


class MessageResponse(BaseModel):
    message: str


class StatusResponse(BaseModel):
    model_config = {"extra": "allow"}

    status: str
