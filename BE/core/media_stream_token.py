"""
Signed token helpers for Twilio Media Stream WebSocket URLs.

Twilio signs the HTTP webhook that returns TwiML, but the subsequent WebSocket
upgrade does not use the same signature header. A short HMAC token in the
generated Stream URL prevents direct connections with guessed lead IDs.
"""

import hashlib
import hmac
import os
from typing import Optional


def media_stream_token_enabled() -> bool:
    raw = os.getenv("MEDIA_STREAM_VALIDATE_TOKEN", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _token_secret() -> str:
    return (
        os.getenv("MEDIA_STREAM_TOKEN_SECRET", "").strip()
        or os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        or os.getenv("API_KEY", "").strip()
    )


def generate_media_stream_token(lead_id: int, twilio_number: str, agent_id: str) -> str:
    secret = _token_secret()
    if not secret:
        return ""

    message = f"{agent_id}:{lead_id}:{twilio_number}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def validate_media_stream_token(
    token: Optional[str],
    lead_id: Optional[str],
    twilio_number: str,
    agent_id: str,
) -> bool:
    if not media_stream_token_enabled():
        return True
    if not token or not lead_id or not lead_id.isdigit():
        return False

    expected = generate_media_stream_token(int(lead_id), twilio_number, agent_id)
    return bool(expected) and hmac.compare_digest(expected, token)
