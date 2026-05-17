"""
Services Module
Business logic layer for campaign management, consent tracking, and lead
management.

Imports are lazy (PEP 562) so importing one service does not pull in the
dependencies of unrelated services. In particular ``twilio_service`` requires
``aiohttp``, which we do not want every service consumer to need at import
time.

Existing call sites that do ``from services import TwilioService`` keep
working unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from .twilio_service import TwilioService  # noqa: F401
    from .websocket_service import (  # noqa: F401
        EventType,
        broadcast_event,
        broadcast_event_sync,
        get_websocket_manager,
    )


__all__ = [
    "TwilioService",
    "get_websocket_manager",
    "broadcast_event",
    "broadcast_event_sync",
    "EventType",
]


_LAZY_ATTRS = {
    "TwilioService": ("services.twilio_service", "TwilioService"),
    "get_websocket_manager": ("services.websocket_service", "get_websocket_manager"),
    "broadcast_event": ("services.websocket_service", "broadcast_event"),
    "broadcast_event_sync": ("services.websocket_service", "broadcast_event_sync"),
    "EventType": ("services.websocket_service", "EventType"),
}


def __getattr__(name: str) -> Any:
    target = _LAZY_ATTRS.get(name)
    if target is None:
        raise AttributeError(f"module 'services' has no attribute {name!r}")
    import importlib

    module = importlib.import_module(target[0])
    value = getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_ATTRS.keys()))
