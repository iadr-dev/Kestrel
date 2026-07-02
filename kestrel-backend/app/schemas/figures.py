from typing import Any

from pydantic import BaseModel, Field


class FigureItem(BaseModel):
    id: str
    name_en: str | None = None
    name_zh: str | None = None
    role: str | None = None
    category: str | None = None
    photo_url: str | None = None
    associated_stocks: list[str] = Field(default_factory=list)


class FigureListResponse(BaseModel):
    data: list[FigureItem] = Field(default_factory=list)
    count: int = 0


class FigureEvent(BaseModel):
    id: str | None = None
    figure_id: str | None = None
    event_type: str | None = None
    title: str | None = None
    description: str | None = None
    date: str | None = None
    impact: str | None = None
    related_stocks: list[str] = Field(default_factory=list)


class FigureEventsResponse(BaseModel):
    data: list[FigureEvent] = Field(default_factory=list)
    count: int = 0


class FigureTimelineResponse(BaseModel):
    figure: dict[str, Any] | None = None
    events: list[FigureEvent] = Field(default_factory=list)


class FigureCategoryItem(BaseModel):
    category: str
    count: int


class FigureCategoriesResponse(BaseModel):
    data: list[FigureCategoryItem] = Field(default_factory=list)
