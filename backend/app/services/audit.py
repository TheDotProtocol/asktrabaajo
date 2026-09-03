"""Audit service — one reusable writer for every future module."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core import context
from app.models.audit import AuditLogEntry
from app.models.enums import AUDIT_RESULT_SUCCESS


def record(
    db: Session,
    *,
    actor_id: Optional[uuid.UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
    result: str = AUDIT_RESULT_SUCCESS,
    metadata: Optional[dict] = None,
) -> AuditLogEntry:
    """Create (but do not commit) one append-only audit entry.

    Request metadata (request id, ip, user agent) is pulled automatically
    from the request context populated by the middleware.
    """
    meta = context.request_meta()
    entry = AuditLogEntry(
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        organization_id=organization_id,
        result=result,
        request_id=meta.get("request_id"),
        ip_address=meta.get("ip_address"),
        user_agent=(meta.get("user_agent") or "")[:255],
        payload=metadata,
    )
    db.add(entry)
    return entry


def record_committed(
    db: Session,
    *,
    actor_id: Optional[uuid.UUID],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
    result: str = AUDIT_RESULT_SUCCESS,
    metadata: Optional[dict] = None,
) -> AuditLogEntry:
    """Write an audit entry in its own transaction.

    Used for events that must be recorded even when the surrounding request
    fails (e.g. denied access attempts) or after the main transaction has
    already been committed.
    """
    entry = record(
        db,
        actor_id=actor_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        organization_id=organization_id,
        result=result,
        metadata=metadata,
    )
    db.commit()
    return entry
