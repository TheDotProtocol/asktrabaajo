"""HTTP middleware: request id + client metadata + access logging."""
from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core import context
from app.core.logging import get_logger
from app.core.security import new_request_id

logger = get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Tag every request with an id, capture client metadata, and log it."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        started = time.monotonic()

        client_ip = request.client.host if request.client else None
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip() or client_ip

        context.set_request_context(
            {
                "request_id": request_id,
                "ip_address": client_ip,
                "user_agent": (request.headers.get("User-Agent") or "")[:255],
                "actor_id": None,
            }
        )

        response = Response()
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.monotonic() - started) * 1000
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "method=%s path=%s status=%d duration_ms=%.1f",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            context.set_request_context({})
        return response
