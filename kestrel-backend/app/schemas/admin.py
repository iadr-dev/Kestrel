from typing import Any

from pydantic import BaseModel, Field


class JobTriggerResponse(BaseModel):
    status: str
    job: str


class JobStatusItem(BaseModel):
    id: str
    schedule: str | None = None
    description: str | None = None


class JobsStatusResponse(BaseModel):
    jobs: list[JobStatusItem] = Field(default_factory=list)
    data_status: dict[str, Any] = Field(default_factory=dict)
