"""Structured logging setup.

Log lines are text with a request id injected from the request context:

    time level logger request_id=<hex> message

NEVER log passwords, tokens, API keys, or personal document contents — the
application code is responsible for not passing them into log statements.
"""
from __future__ import annotations

import logging
import sys
import threading

from app.core.config import Settings

_configured = False
_configured_lock = threading.Lock()

ROOT_LOGGER_NAME = "asktrabaajo"


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            from app.core import context

            record.request_id = context.request_meta().get("request_id") or "-"
        except Exception:  # pragma: no cover - defensive
            record.request_id = "-"
        return True


def setup_logging(settings: Settings) -> None:
    """Configure root logging once per process."""
    global _configured
    with _configured_lock:
        if _configured:
            return

        level = logging.DEBUG if settings.environment == "development" else logging.INFO
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s request_id=%(request_id)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        handler.addFilter(RequestIdFilter())

        root = logging.getLogger(ROOT_LOGGER_NAME)
        root.setLevel(level)
        root.handlers.clear()
        root.addHandler(handler)
        root.propagate = False

        # Silence noisy libraries.
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
