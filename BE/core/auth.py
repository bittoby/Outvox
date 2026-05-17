"""
API-key authentication middleware.

The shared secret is taken from ``config.security.API_KEY``. Requests must
present it in either:

* the ``X-API-Key`` header, or
* the ``Authorization: Bearer <key>`` header.

Requests to paths listed in ``AUTH_EXEMPT_PREFIXES`` skip the check — used
for health probes, Twilio webhooks, and the OpenAPI docs.

If ``API_KEY`` is unset, a loud warning is logged at process start and the
middleware allows all requests through. **Do not** run an internet-reachable
deployment with ``API_KEY`` unset.

Read methods (``GET``/``HEAD``/``OPTIONS``) are NOT exempt — even read access
to lead lists and call transcripts is sensitive. If you want to expose
read-only paths publicly, add them to ``AUTH_EXEMPT_PREFIXES``.
"""

import hmac
import logging
from typing import Iterable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


def _parse_prefixes(raw: str) -> list[str]:
    return [p.strip() for p in (raw or "").split(",") if p.strip()]


def _extract_presented_key(request: Request) -> str | None:
    """Return the API key the caller presented, if any."""
    header_key = request.headers.get("x-api-key")
    if header_key:
        return header_key.strip()
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that enforces a shared API key on protected routes."""

    def __init__(self, app, *, expected_key: str, exempt_prefixes: Iterable[str]):
        super().__init__(app)
        self.expected_key = (expected_key or "").strip()
        self.exempt_prefixes = tuple(exempt_prefixes)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path or "/"

        # CORS preflight must pass to the CORS middleware without auth.
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip auth for explicitly-exempt prefixes.
        if any(path == p or path.startswith(p.rstrip("/") + "/") or path.startswith(p) for p in self.exempt_prefixes):
            return await call_next(request)

        # If no key is configured, allow but the startup banner has already
        # warned about it.
        if not self.expected_key:
            return await call_next(request)

        presented = _extract_presented_key(request)
        if not presented or not hmac.compare_digest(presented, self.expected_key):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "unauthorized",
                    "message": (
                        "Missing or invalid API key. Provide it in the "
                        "X-API-Key header or as a Bearer token."
                    ),
                },
            )

        return await call_next(request)


def install_api_key_auth(app, *, service_name: str) -> None:
    """
    Attach :class:`APIKeyAuthMiddleware` to a FastAPI app and log the resulting
    security posture.
    """
    try:
        from config import config
        expected_key = config.security.API_KEY
        exempt_prefixes = _parse_prefixes(config.security.AUTH_EXEMPT_PREFIXES)
    except Exception:
        logger.exception("Could not load security config; auth middleware disabled.")
        return

    if not expected_key:
        logger.warning(
            "⚠️  %s starting WITHOUT an API key — all requests will be accepted. "
            "Set API_KEY in your environment before exposing this service. "
            "See SECURITY.md.",
            service_name,
        )
    else:
        logger.info(
            "🔐 %s: API-key auth enabled. Exempt prefixes: %s",
            service_name,
            ", ".join(exempt_prefixes) or "(none)",
        )

    app.add_middleware(
        APIKeyAuthMiddleware,
        expected_key=expected_key,
        exempt_prefixes=exempt_prefixes,
    )
