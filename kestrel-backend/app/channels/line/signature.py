"""LINE webhook signature verification using HMAC-SHA256."""

import base64
import hashlib
import hmac


def verify_line_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    """Verify X-Line-Signature header against request body."""
    computed = hmac.new(
        channel_secret.encode("utf-8"), body, hashlib.sha256
    ).digest()
    expected = base64.b64encode(computed).decode("utf-8")
    return hmac.compare_digest(signature, expected)
