"""Voice endpoints — Speech-to-Text (Whisper) and Text-to-Speech.

Thin controllers: transport, provider failover, and TLS/retry live in
`MediaService` (app/services/platform/media_service.py). Whisper auto-detects the
spoken language (handles English + Traditional Chinese; no language is forced).
"""

from typing import Any

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.dependencies import get_current_user_id, get_media_service
from app.schemas.voice import TranscribeResponse
from app.services.platform.media_service import MediaService

router = APIRouter(prefix="/voice", tags=["Voice"])


class SpeakRequest(BaseModel):
    text: str
    voice: str = "nova"
    model: str = "tts-1"


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
    _: str = Depends(get_current_user_id),
    media: MediaService = Depends(get_media_service),
) -> dict[str, Any]:
    """Transcribe an audio file to text (auto-detects EN / zh-TW).

    `_` (the authenticated user id) gates access — must be logged in — but the
    transcription itself is user-agnostic, so the value isn't read.
    """
    content = await file.read()
    result = await media.transcribe(content, file.filename or "audio.webm", file.content_type)
    if result.error:
        return {"error": result.error, "text": result.text}
    return {"text": result.text, "duration": result.duration}


@router.post("/speak")
async def synthesize_speech(
    request: SpeakRequest,
    _: str = Depends(get_current_user_id),
    media: MediaService = Depends(get_media_service),
) -> Response:
    """Synthesize speech from text (returns audio/mpeg).

    The frontend plays the returned MP3; on failure it falls back to the browser's
    speechSynthesis.
    """
    result = await media.synthesize(request.text, voice=request.voice, model=request.model)
    if result.error or result.audio is None:
        status = 400 if result.error == "Text cannot be empty" else 502
        return JSONResponse({"error": result.error or "TTS failed"}, status_code=status)
    return Response(content=result.audio, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
