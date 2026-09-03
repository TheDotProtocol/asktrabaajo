"""In-app notification service — minimal, focused, anti-spam by construction.

Phase 5 covers the jobseeker feed only (application/interview/offer/document/
career events). The unified multi-channel architecture (email/SMS/push/voice
with per-user preferences) lands in a later phase; ``kind`` and ``user_id``
are already modeled so that layer can attach without remodelling.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utc_now_naive
from app.models.career import UserNotification
from app.models.enums import NOTIFICATION_KIND_SYSTEM


def notify(
    db: Session,
    user_id: uuid.UUID,
    title: str,
    body: Optional[str] = None,
    kind: str = NOTIFICATION_KIND_SYSTEM,
) -> UserNotification:
    entry = UserNotification(user_id=user_id, kind=kind, title=title, body=body)
    db.add(entry)
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
