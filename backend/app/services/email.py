"""Outbound email abstraction.

No vendor is assumed. When SMTP credentials are configured (the existing
SMTP_* environment variables used by the legacy email service), messages go
out via aiosmtplib; otherwise (development/test) they are logged through the
``asktrabaajo.mail`` logger — never logged: the message body may contain
tokens, so only metadata is logged and the body is delivered or dropped.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

from app.core.logging import get_logger

logger = get_logger("mail")

_SMTP_HOST = os.getenv("SMTP_HOST", "")
_SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
_SMTP_USER = os.getenv("SMTP_USER", "")
_SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
_SMTP_FROM = os.getenv("SMTP_FROM", "AskTrabaajo <noreply@asktrabaajo.example>")

SMTP_CONFIGURED = bool(_SMTP_HOST and _SMTP_USER and _SMTP_PASSWORD)


def smtp_configured() -> bool:
    return SMTP_CONFIGURED


def send(to: str, subject: str, body_text: str) -> bool:
    """Send one message. Returns True when delivered, False when only logged.

    In development/test (no SMTP_* config) the message is intentionally NOT
    logged in full — only delivery metadata — so verification/reset tokens
    never appear in application logs.
    """
    if not SMTP_CONFIGURED:
        logger.info(
            "email.deferred transport=console to=%s subject=%r body_chars=%d",
            to,
            subject,
            len(body_text),
        )
        return False
    try:
        import aiosmtplib  # type: ignore

        message = (
            f"From: {_SMTP_FROM}\n"
            f"To: {to}\n"
            f"Subject: {subject}\n\n"
            f"{body_text}"
        )
        aiosmtplib.send(
            message,
            hostname=_SMTP_HOST,
            port=_SMTP_PORT,
            username=_SMTP_USER,
            password=_SMTP_PASSWORD,
            start_tls=True,
        )
        logger.info("email.sent to=%s subject=%r", to, subject)
        return True
    except Exception:  # noqa: BLE001 - delivery must never break the request
        logger.error("email.send_failed to=%s subject=%r", to, subject, exc_info=True)
        return False
