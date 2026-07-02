from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Existing models ---

class PortfolioHolding(BaseModel):
    stock_id: str
    shares: float
    avg_cost: float | None = None
    added_at: datetime | None = None


class PortfolioCreate(BaseModel):
    name: str
    holdings: list[PortfolioHolding] = Field(default_factory=list)


class PortfolioResponse(BaseModel):
    id: str
    name: str
    holdings: list[PortfolioHolding] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WatchlistItem(BaseModel):
    stock_id: str
    note: str | None = None
    added_at: datetime | None = None


class WatchlistCreate(BaseModel):
    name: str
    items: list[WatchlistItem] = Field(default_factory=list)


class WatchlistResponse(BaseModel):
    id: str
    name: str
    market: str | None = "TW"
    items: list[WatchlistItem] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


# --- Request models ---

class CreatePortfolioRequest(BaseModel):
    name: str
    holdings: list[PortfolioHolding] = Field(default_factory=list)


class CreateWatchlistRequest(BaseModel):
    name: str
    market: str = "TW"


class AddWatchlistItemRequest(BaseModel):
    watchlist_id: str
    stock_id: str
    note: str | None = None


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    custom_api_keys: dict[str, str] | None = None


class AgentSettingsRequest(BaseModel):
    response_style: str | None = None
    custom_instructions: str | None = None
    focus_areas: list[str] | None = None


class UIPreferencesRequest(BaseModel):
    theme: str | None = None
    language: str | None = None
    market_preference: str | None = None


# --- Response models ---

class PortfolioListResponse(BaseModel):
    data: list[PortfolioResponse] = Field(default_factory=list)
    count: int = 0


class PortfolioCreateResponse(BaseModel):
    data: PortfolioResponse


class WatchlistListResponse(BaseModel):
    data: list[WatchlistResponse] = Field(default_factory=list)
    count: int = 0


class WatchlistCreateResponse(BaseModel):
    data: WatchlistResponse


class WatchlistItemAddResponse(BaseModel):
    status: str
    item: dict[str, Any] = Field(default_factory=dict)


class WatchlistItemDeleteResponse(BaseModel):
    status: str
    stock_id: str


class UserProfileResponse(BaseModel):
    id: str
    display_name: str | None = None
    email: str | None = None
    tier: str = "free"
    picture_url: str | None = None
    custom_api_keys: dict[str, str] = Field(default_factory=dict)
    # Server-computed feature entitlements (single source of truth for the client).
    entitlements: dict[str, Any] = Field(default_factory=dict)


class ProfileUpdateResponse(BaseModel):
    status: str
    display_name: str | None = None
    custom_api_keys_set: list[str] = Field(default_factory=list)


class AgentSettingsResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)


class UIPreferencesResponse(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
