"""Canonical realtime event service (Phase 9).

Domain services call ``emit`` with a whitelisted, minimal payload. The event
log is authorization-aware by construction:

- Events are addressed to ONE user (``recipient_user_id``) or to an
  ORGANIZATION (``organization_id`` + ``org_scope=True`` — visible to every
  member of that org, and only to them).
- ``list_for_user`` returns only events the caller may see: their own plus
  org-scoped events of organizations they belong to. A stranger can never
  enumerate another tenant's events, even knowing event UUIDs.
- Payloads are whitelisted metadata (event type, resource reference,
  timestamps). Message bodies, document contents, private Work ID sections
  and audit contents are never stored here.

The transport is decoupled: a future WebSocket/SSE layer reads the same
table. Polling (``GET /api/v1/events?after=<iso>``) is the Phase 9
transport — documented honestly in the phase report.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import EVENT_TYPES
from app.models.platform import PlatformEvent
from app.models.tenancy import Membership


def emit(
    db: Session,
    *,
    event_type: str,
    resource_type: str,
    resource_id,
    recipient_user_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    org_scope: bool = False,
    actor_user_id: Optional[uuid.UUID] = None,
    payload: Optional[dict] = None,
) -> PlatformEvent:
    """Add one event row (does NOT commit — callers own their transaction).

    Exactly one addressing mode is expected: a direct recipient OR an
    organization-scoped event (an event may carry both the org link for
    tenant attribution and the org_scope flag; when org_scope is True the
    ``organization_id`` also routes to the org's members).
    """
    if event_type not in EVENT_TYPES:
        # Controlled set: unknown event types are rejected rather than
        # silently stored (no arbitrary strings).
        from app.core.errors import InvalidInputError

        raise InvalidInputError(f"Unknown event type '{event_type}'.")
    if recipient_user_id is None and organization_id is None:
        from app.core.errors import InvalidInputError

        raise InvalidInputError("An event must have a recipient or an organization.")
    event = PlatformEvent(
        event_type=event_type,
        recipient_user_id=recipient_user_id,
        organization_id=organization_id,
        org_scope=org_scope,
        resource_type=resource_type,
        resource_id=str(resource_id)[:64],
        actor_user_id=actor_user_id,
        payload=payload or {},
    )
    db.add(event)
    return event


def _membership_org_ids(db: Session, user_id: uuid.UUID) -> list:
    return list(
        db.scalars(
            select(Membership.organization_id).where(Membership.user_id == user_id)
        ).all()
    )


def list_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    after: Optional[str] = None,
    limit: int = 100,
    unread_only: bool = False,
) -> list:
    """Events the caller may see: direct + their orgs' scoped events.

    ``after`` is an ISO-8601 timestamp (client-side cursor) — events newer
    than it are returned in ascending order for stable polling.
    """
    org_ids = _membership_org_ids(db, user_id)
    conditions = [PlatformEvent.recipient_user_id == user_id]
    if org_ids:
        conditions.append(
            (PlatformEvent.org_scope.is_(True))
            & (PlatformEvent.organization_id.in_(org_ids))
        )
    from sqlalchemy import or_

    query = select(PlatformEvent).where(or_(*conditions))
    if after:
        from app.core.timeutil import utc_now_naive
        from datetime import datetime

        try:
            cursor = datetime.fromisoformat(after)
        except ValueError:
            cursor = utc_now_naive()
        query = query.where(PlatformEvent.created_at > cursor)
    if unread_only:
        query = query.where(PlatformEvent.read_at.is_(None))
    events = db.scalars(
        query.order_by(PlatformEvent.created_at.asc()).limit(max(1, min(limit, 200)))
    ).all()
    return [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "organization_id": str(e.organization_id) if e.organization_id else None,
            "payload": e.payload or {},
            "read": e.read_at is not None,
            "created_at": e.created_at,
        }
        for e in events
    ]


def mark_read(db: Session, user_id: uuid.UUID, event_ids: list) -> int:
    """Mark the caller's OWN events as read (never another user's)."""
    from app.core.timeutil import utc_now_naive

    marked = 0
    for event_id in event_ids:
        try:
            parsed = uuid.UUID(str(event_id))
        except (ValueError, TypeError):
            continue
        event = db.get(PlatformEvent, parsed)
        if event is None:
            continue
        visible = event.recipient_user_id == user_id
        if not visible and event.org_scope and event.organization_id:
            visible = event.organization_id in _membership_org_ids(db, user_id)
        if not visible:
            continue
        event.read_at = utc_now_naive()
        marked += 1
    db.commit()
    return marked