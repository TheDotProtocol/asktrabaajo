"""Per-request context (request id, client metadata) via contextvars.

The middleware populates this for every request; audit and logging consume
it so call sites do not have to thread request metadata manually.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Dict, Optional

_request_ctx: ContextVar[Dict[str, Any]] = ContextVar("request_ctx", default={})


def set_request_context(meta: Dict[str, Any]) -> None:
    _request_ctx.set(meta or {})


def get_request_context() -> Dict[str, Any]:
    return _request_ctx.get()


def request_meta() -> Dict[str, Any]:
    """Snapshot of the metadata fields used by audit + logging."""
    ctx = _request_ctx.get()
    return {
        "request_id": ctx.get("request_id"),
        "ip_address": ctx.get("ip_address"),
        "user_agent": ctx.get("user_agent"),
        "actor_id": ctx.get("actor_id"),
    }
