"""
Twilio webhook signature validation helpers.

Twilio signs inbound webhook requests with the account auth token. Validation is
enabled by default when TWILIO_AUTH_TOKEN is configured. Set
TWILIO_VALIDATE_SIGNATURE=false only for local mock/demo traffic.
"""

import os
from urllib.parse import urlsplit, urlunsplit

from fastapi import HTTPException, Request
from twilio.request_validator import RequestValidator


def _signature_validation_enabled() -> bool:
    raw = os.getenv("TWILIO_VALIDATE_SIGNATURE", "true").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _external_url(request: Request) -> str:
    override_base = os.getenv("PUBLIC_WEBHOOK_BASE_URL", "").strip().rstrip("/")
    if not override_base:
        return str(request.url)

    split_request = urlsplit(str(request.url))
    split_base = urlsplit(override_base)
    return urlunsplit(
        (
            split_base.scheme,
            split_base.netloc,
            split_request.path,
            split_request.query,
            "",
        )
    )


async def validate_twilio_request(request: Request, form_data=None) -> None:
    """
    Raise HTTP 403 if the request is not signed by Twilio.

    `PUBLIC_WEBHOOK_BASE_URL` should match the public scheme/host Twilio calls
    when the app sits behind ngrok, Nginx, or another reverse proxy.
    """
    if not _signature_validation_enabled():
        return

    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    if not auth_token:
        raise HTTPException(
            status_code=500,
            detail="TWILIO_AUTH_TOKEN is required for Twilio signature validation",
        )

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        raise HTTPException(status_code=403, detail="Missing X-Twilio-Signature")

    if form_data is None:
        form_data = await request.form()

    params = dict(request.query_params)
    params.update(dict(form_data))
    validator = RequestValidator(auth_token)
    if not validator.validate(_external_url(request), params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
