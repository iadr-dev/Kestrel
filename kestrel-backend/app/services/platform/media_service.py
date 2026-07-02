"""MediaService — speech-to-text and text-to-speech over OpenAI-compatible APIs.

Centralizes the audio transport so endpoints stay thin (controller → service):
- One ordered list of backends (base_url + which Settings key holds the token),
  tried in turn until one succeeds. Add a provider by appending one tuple.
- Shared TLS verification + transient-retry via app.providers.http.
- No FastAPI types here, so it's independently unit-testable and reusable from
  scripts/jobs (e.g. batch transcription) — not just HTTP handlers.

NOTE on ChatAnywhere: its FREE tier serves only chat + embeddings (audio returns
403), so audio backends list OpenAI first. A ChatAnywhere PAID key could be added
as a fallback tuple without touching any endpoint code.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.providers.http import request_with_retry, verify_tls

logger = get_logger(__name__)

# OpenAI TTS voices accepted by /audio/speech.
TTS_VOICES = frozenset({"alloy", "echo", "fable", "onyx", "nova", "shimmer"})

_AUDIO_TIMEOUT = 30.0


@dataclass(frozen=True)
class _Backend:
    """An OpenAI-compatible audio backend: base URL + the Settings attr holding its key."""

    base_url: str
    key_attr: str


# Ordered by preference. OpenAI first for audio (ChatAnywhere free tier rejects it).
_AUDIO_BACKENDS: tuple[_Backend, ...] = (
    _Backend("https://api.openai.com/v1", "openai_api_key"),
)


@dataclass(frozen=True)
class TranscriptResult:
    text: str
    duration: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class SpeechResult:
    audio: bytes | None = None
    error: str | None = None


class MediaService:
    """STT/TTS over one or more OpenAI-compatible providers with failover."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _configured_backends(self) -> list[_Backend]:
        """Backends whose API key is present, in preference order."""
        return [b for b in _AUDIO_BACKENDS if getattr(self._settings, b.key_attr, None)]

    async def transcribe(
        self, content: bytes, filename: str, content_type: str | None
    ) -> TranscriptResult:
        """Whisper speech-to-text. Language is auto-detected (handles EN + zh-TW)."""
        if not content:
            return TranscriptResult(text="", error="Empty audio file")

        backends = self._configured_backends()
        if not backends:
            return TranscriptResult(text="", error="no transcription backend configured")

        last_error = ""
        async with httpx.AsyncClient(timeout=_AUDIO_TIMEOUT, verify=verify_tls()) as client:
            for backend in backends:
                key = getattr(self._settings, backend.key_attr)
                try:
                    resp = await request_with_retry(
                        partial(
                            client.post,
                            f"{backend.base_url}/audio/transcriptions",
                            headers={"Authorization": f"Bearer {key}"},
                            # No `language` → Whisper auto-detects EN / zh-TW.
                            data={"model": "whisper-1"},
                            files={"file": (filename, content, content_type or "audio/webm")},
                        ),
                        label="whisper_transcribe",
                    )
                except httpx.HTTPError as e:
                    last_error = f"{backend.base_url}: {e}"
                    continue
                if resp.status_code == 200:
                    body = resp.json()
                    return TranscriptResult(text=body.get("text", ""), duration=body.get("duration"))
                last_error = f"{backend.base_url}: HTTP {resp.status_code}"

        logger.warning("transcribe_failed", error=last_error)
        return TranscriptResult(text="", error=f"Transcription failed ({last_error})")

    async def synthesize(self, text: str, voice: str = "nova", model: str = "tts-1") -> SpeechResult:
        """Text-to-speech → MP3 bytes. Returns SpeechResult(error=...) on failure."""
        text = text.strip()
        if not text:
            return SpeechResult(error="Text cannot be empty")
        text = text[:4096]  # tts-1 input cap
        if voice not in TTS_VOICES:
            voice = "nova"

        backends = self._configured_backends()
        if not backends:
            return SpeechResult(error="no TTS backend configured")

        last_error = ""
        async with httpx.AsyncClient(timeout=_AUDIO_TIMEOUT, verify=verify_tls()) as client:
            for backend in backends:
                key = getattr(self._settings, backend.key_attr)
                try:
                    resp = await request_with_retry(
                        partial(
                            client.post,
                            f"{backend.base_url}/audio/speech",
                            headers={"Authorization": f"Bearer {key}"},
                            json={"model": model, "input": text, "voice": voice},
                        ),
                        label="tts_speak",
                    )
                except httpx.HTTPError as e:
                    last_error = f"{backend.base_url}: {e}"
                    continue
                if resp.status_code == 200:
                    return SpeechResult(audio=resp.content)
                last_error = f"{backend.base_url}: HTTP {resp.status_code}"

        logger.warning("tts_failed", error=last_error)
        return SpeechResult(error=f"TTS failed ({last_error})")
