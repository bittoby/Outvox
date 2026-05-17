"""
Pure SMS reply classifier.

Splits the regex/keyword logic out of :mod:`services.consent_tracker` so it can
be unit-tested without importing Twilio or pyodbc. ``consent_tracker`` still
re-exports the public symbols below for backward compatibility.

Classification rules:

* ``STOP`` keywords are checked first — opt-out compliance has priority.
* ``YES`` keywords are checked next.
* Anything else (including unrecognized text) is ``OTHER`` and surfaces for
  manual review.
"""

from __future__ import annotations

import re
from typing import Literal

Classification = Literal["YES", "STOP", "OTHER"]


YES_KEYWORDS: list[str] = [
    "yes", "yeah", "yea", "yep", "sure", "ok", "okay", "k",
    "interested", "call me", "call", "contact me", "reach out",
    "sounds good", "that works", "perfect", "great", "absolutely",
    "definitely", "confirm", "confirmed", "accept", "agree",
    "si", "sí",  # Spanish
]

STOP_KEYWORDS: list[str] = [
    "stop", "unsubscribe", "remove", "no", "nope", "nah",
    "don't", "dont", "never", "leave me alone", "not interested",
    "remove me", "take me off", "delete", "cancel", "quit",
    "end", "opt out", "optout", "opt-out", "do not contact",
    "do not call", "don't call", "dont call", "no thanks",
]


_NON_TEXT_RE = re.compile(r"[^a-z0-9\s]")


def _normalize(body: str) -> tuple[str, list[str]]:
    normalized = _NON_TEXT_RE.sub("", body.lower().strip())
    return normalized, normalized.split()


def _matches(keywords: list[str], normalized: str, words: list[str]) -> bool:
    for keyword in keywords:
        if " " in keyword:
            if keyword in normalized:
                return True
        else:
            if keyword in words:
                return True
    return False


def classify_reply(body: str | None) -> Classification:
    """Classify a raw SMS body as ``YES`` / ``STOP`` / ``OTHER``."""
    if not body or not isinstance(body, str):
        return "OTHER"

    normalized, words = _normalize(body)

    if _matches(STOP_KEYWORDS, normalized, words):
        return "STOP"
    if _matches(YES_KEYWORDS, normalized, words):
        return "YES"
    return "OTHER"
