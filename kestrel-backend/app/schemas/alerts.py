from typing import Any

from pydantic import BaseModel, Field

# --- Request Models ---

class CreateAlertRequest(BaseModel):
    category: str | None = None
    alert_type: str
    stock_id: str | None = None
    condition: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None
    is_recurring: bool = False
    channels: list[str] = Field(default_factory=list)


class UpdatePreferencesRequest(BaseModel):
    channels: list[str] | None = None
    enabled_categories: list[str] | None = None
    quiet_start: str | None = None
    quiet_end: str | None = None
    daily_limit: int | None = None
    morning_digest: bool | None = None


# --- Response Models ---

class AlertRuleItem(BaseModel):
    id: str
    category: str | None = None
    alert_type: str | None = None
    stock_id: str | None = None
    condition: dict[str, Any] | None = None
    is_active: bool = True
    is_recurring: bool = False
    trigger_count: int = 0
    last_triggered_at: str | None = None


class AlertRuleListResponse(BaseModel):
    data: list[AlertRuleItem] = Field(default_factory=list)
    count: int = 0


class AlertCreateResponse(BaseModel):
    status: str
    id: str


class AlertToggleResponse(BaseModel):
    status: str
    is_active: bool


class AlertPreferences(BaseModel):
    channels: list[str] = Field(default_factory=list)
    enabled_categories: list[str] = Field(default_factory=list)
    quiet_start: str | None = None
    quiet_end: str | None = None
    daily_limit: int | None = None
    morning_digest: bool = False


class AlertPreferencesResponse(BaseModel):
    data: AlertPreferences


class AlertHistoryItem(BaseModel):
    id: str
    stock_id: str | None = None
    alert_type: str | None = None
    message: str | None = None
    ai_context: str | None = None
    channels_sent: list[str] = Field(default_factory=list)
    delivered_at: str | None = None


class AlertHistoryResponse(BaseModel):
    data: list[AlertHistoryItem] = Field(default_factory=list)
    count: int = 0
