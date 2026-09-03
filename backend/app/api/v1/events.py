"""/api/v1/events — the canonical realtime event feed (Phase 9).

The feed returns ONLY events the caller may see (their own + their
organizations' scoped events). It is the polling transport for the future
WebSocket/SSE layer: the event table and this contract stay identical when a
managed transport replaces the poll loop.

Events never contain message bodies, document contents or private Work ID
data — payloads are whitelisted metadata.
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.services import events as events_service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=dict)
def my_events(
    after: Optional[str] = Query(None, max_length=64, description="ISO cursor"),
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    items = events_service.list_for_user(
        db, user.id, after=after, limit=limit, unread_only=unread_only
    )
    return {
        "items": items,
        "count": len(items),
        "next_after": items[-1]["created_at"].isoformat() if items else None,
    }


@router.post("/read", response_model=dict)
def mark_events_read(
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    ids: list = body.get("ids") or []
    marked = events_service.mark_read(db, user.id, [str(i) for i in ids[:200]])
    return {"marked": marked}