"""Notification service — in-app feed (Phases 5–8) + out-of-band foundation
(Phase 9).

The in-app feed stays the primary channel (anti-spam by construction; never
message bodies). Phase 9 adds a provider-neutral OUT-OF-BAND abstraction:

- ``deliver`` fans a single domain event out to every channel the user has
  opted into. In-app is always on; email/push/SMS are off until the user
  enables them (``notification_preferences``).
- Out-of-band messages are built from a SAFE title + safe context only —
  they say "you have a new offer in AskTrabaajo", never dumping private
  Work ID data or document contents.
- No commercial provider is assumed: the email channel reuses the existing
  SMTP-or-console abstraction; push/SMS are declared but deferred.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utc_now_naive
from app.models.career import UserNotification
from app.models.enums import (
    NOTIFICATION_CHANNEL_EMAIL,
    NOTIFICATION_CHANNEL_IN_APP,
    NOTIFICATION_CHANNEL_PUSH,
    NOTIFICATION_CHANNEL_SMS,
    NOTIFICATION_KIND_SYSTEM,
)
from app.models.identity import User
from app.models.platform import NotificationPreference


class NotificationChannel:
    """Provider-neutral channel contract. Channels render a SAFE message from
    (title, kind, context) — never raw payloads."""

    name = "in_app"
    deferred = False

    def deliver(
        self,
        db: Session,
        user: User,
        *,
        title: str,
        kind: str,
        context: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError


class InAppChannel(NotificationChannel):
    name = NOTIFICATION_CHANNEL_IN_APP

    def deliver(self, db, user, *, title, kind, context=None) -> bool:
        entry = UserNotification(
            user_id=user.id, kind=kind, title=title, body=context
        )
        db.add(entry)
        return True


class EmailChannel(NotificationChannel):
    """Out-of-band email. Uses the existing provider-neutral SMTP/console
    transport; the message NEVER contains private data or document contents."""

    name = NOTIFICATION_CHANNEL_EMAIL

    def deliver(self, db, user, *, title, kind, context=None) -> bool:
        from app.services import email as email_service

        safe_body = (
            f"You have a new {kind.replace('_', ' ')} update in AskTrabaajo.\n"
            f"{context or ''}\n\n"
            "Sign in to AskTrabaajo to review it."
        )[:2000]
        return email_service.send(user.email, title, safe_body)


class DeferredChannel(NotificationChannel):
    """Push/SMS are declared for the abstraction but not implemented — no
    provider is configured, and nothing is sent."""

    deferred = True

    def __init__(self, name: str) -> None:
        self.name = name

    def deliver(self, db, user, *, title, kind, context=None) -> bool:
        return False


CHANNEL_REGISTRY: dict = {
    NOTIFICATION_CHANNEL_IN_APP: InAppChannel(),
    NOTIFICATION_CHANNEL_EMAIL: EmailChannel(),
    NOTIFICATION_CHANNEL_PUSH: DeferredChannel(NOTIFICATION_CHANNEL_PUSH),
    NOTIFICATION_CHANNEL_SMS: DeferredChannel(NOTIFICATION_CHANNEL_SMS),
}


def channel_preferences(db: Session, user_id: uuid.UUID) -> dict:
    """Enabled channels for a user (in-app always on)."""
    rows = db.scalars(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.enabled.is_(True),
        )
    ).all()
    enabled = {r.channel for r in rows}
    enabled.add(NOTIFICATION_CHANNEL_IN_APP)
    return enabled


def set_channel_preference(
    db: Session, user_id: uuid.UUID, channel: str, enabled: bool
) -> NotificationPreference:
    if channel not in CHANNEL_REGISTRY:
        raise ValueError(f"Unknown notification channel '{channel}'.")
    row = db.get(NotificationPreference, (user_id, channel))
    if row is None:
        row = NotificationPreference(user_id=user_id, channel=channel, enabled=enabled)
        db.add(row)
    else:
        row.enabled = enabled
    db.commit()
    db.refresh(row)
    return row


def notify(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    body: Optional[str] = None,
    kind: str = NOTIFICATION_KIND_SYSTEM,
) -> UserNotification:
    """Deliver an event to the in-app feed (and opted-in out-of-band
    channels). The in-app entry is always created; out-of-band delivery is
    best-effort and never breaks the request."""
    user = db.get(User, user_id)
    if user is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("User not found.")
    entry = UserNotification(user_id=user_id, kind=kind, title=title, body=body)
    db.add(entry)
    enabled = channel_preferences(db, user_id)
    for channel_name in sorted(enabled - {NOTIFICATION_CHANNEL_IN_APP}):
        channel = CHANNEL_REGISTRY[channel_name]
        try:
            channel.deliver(db, user, title=title, kind=kind, context=body)
        except Exception:  # noqa: BLE001 — delivery must never break the request
            import logging

            logging.getLogger("asktrabaajo.notifications").error(
                "notification.channel_failed channel=%s user=%s",
                channel_name, user_id, exc_info=True,
            )
    db.commit()
    db.refresh(entry)
    return entry


def list_for_user(
    db: Session, user_id: uuid.UUID, limit: int = 30, unread_only: bool = False
) -> list:
    query = select(UserNotification).where(UserNotification.user_id == user_id)
    if unread_only:
        query = query.where(UserNotification.read_at.is_(None))
    query = query.order_by(UserNotification.created_at.desc()).limit(limit)
    return db.scalars(query).all()


def mark_read(db: Session, user_id: uuid.UUID, notification_id: uuid.UUID) -> bool:
    entry = db.get(UserNotification, notification_id)
    if entry is None or entry.user_id != user_id:
        return False
    entry.read_at = utc_now_naive()
    db.commit()
    return True


def mark_all_read(db: Session, user_id: uuid.UUID) -> int:
    entries = db.scalars(
        select(UserNotification).where(
            UserNotification.user_id == user_id,
            UserNotification.read_at.is_(None),
        )
    ).all()
    for entry in entries:
        entry.read_at = utc_now_naive()
    db.commit()
    return len(entries)


def unread_count(db: Session, user_id: uuid.UUID) -> int:
    return len(
        db.scalars(
            select(UserNotification.id).where(
                UserNotification.user_id == user_id,
                UserNotification.read_at.is_(None),
            )
        ).all()
    )
