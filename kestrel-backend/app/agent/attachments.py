"""Chat attachment processing — split user uploads into vision image blocks and
decoded text context.

Images (png/jpeg/webp/gif) become OpenAI-format `image_url` content blocks that a
vision model reads directly (e.g. a user uploads a K-line screenshot or a 財報
table and asks for analysis). Text-based documents (csv/json/txt/markdown) are
decoded from their data URI and inlined as text so any model can use them.

Binary documents we can't parse without extra deps (PDF, xlsx) are surfaced as a
short note rather than silently dropped, so the model can tell the user.
"""

import base64
import binascii
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

# Vision-capable image types. gif is accepted but only the first frame is used.
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}

# Text-based documents we can decode and inline directly.
_TEXT_TYPES = {
    "text/plain",
    "text/csv",
    "text/markdown",
    "application/json",
    "text/json",
}

# Cap inlined doc text so a huge CSV can't blow the context window. ~40k chars
# (~11k tokens) fits the header plus several rows of a wide TW financial-statement
# CSV (200+ columns), while staying well within a 128k-context model's budget.
_MAX_DOC_CHARS = 40_000


def _decode_data_url(data_url: str) -> bytes | None:
    """Decode the base64 payload of a `data:<mime>;base64,<payload>` URI."""
    if "," not in data_url:
        return None
    payload = data_url.split(",", 1)[1]
    try:
        return base64.b64decode(payload)
    except (binascii.Error, ValueError):
        return None


def process_attachments(
    attachments: list[Any] | None,
) -> tuple[list[dict[str, Any]], str]:
    """Split attachments into (image content blocks, extracted text context).

    Each attachment is an object with `.name`, `.type`, `.data_url`. Returns:
    - image_blocks: OpenAI-format `{"type": "image_url", "image_url": {"url": ...}}`
      blocks to merge into the user turn (empty if no images).
    - doc_text: a single string of decoded text-doc contents (empty if none),
      ready to append to the user's message as context.
    """
    if not attachments:
        return [], ""

    image_blocks: list[dict[str, Any]] = []
    doc_parts: list[str] = []

    for att in attachments:
        mime = (getattr(att, "type", "") or "").lower()
        name = getattr(att, "name", "file")
        data_url = getattr(att, "data_url", "") or ""

        if mime in _IMAGE_TYPES:
            # Pass the data URI straight through — OpenAI-compatible vision APIs
            # accept base64 data URIs in image_url.url.
            image_blocks.append({"type": "image_url", "image_url": {"url": data_url}})
            continue

        if mime in _TEXT_TYPES or mime.startswith("text/"):
            raw = _decode_data_url(data_url)
            if raw is None:
                logger.warning("attachment_decode_failed", name=name, mime=mime)
                continue
            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:
                logger.warning("attachment_text_decode_failed", name=name)
                continue
            if len(text) > _MAX_DOC_CHARS:
                text = text[:_MAX_DOC_CHARS] + "\n…(truncated)"
            doc_parts.append(f"[Attached file: {name}]\n{text}")
            continue

        # Unsupported binary doc (PDF, xlsx, …) — note it so the model can respond
        # honestly rather than pretending to have read it.
        doc_parts.append(
            f"[Attached file '{name}' ({mime}) could not be read — ask the user to "
            f"paste the relevant text or upload an image/CSV instead.]"
        )

    doc_text = "\n\n".join(doc_parts)
    return image_blocks, doc_text
