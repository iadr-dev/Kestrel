from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str


class DBHealthResponse(BaseModel):
    duckdb: dict[str, Any] = Field(default_factory=dict)
    sqlalchemy: dict[str, Any] = Field(default_factory=dict)
    cache: dict[str, Any] = Field(default_factory=dict)


class ProviderHealthResponse(BaseModel):
    providers: dict[str, Any] = Field(default_factory=dict)
