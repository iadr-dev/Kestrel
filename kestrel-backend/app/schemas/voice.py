from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    text: str
    duration: float | None = None
    error: str | None = None
