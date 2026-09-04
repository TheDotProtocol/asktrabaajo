"""Athena API — the only boundary to the controlled intelligence layer.

Every route is authenticated; no anonymous Athena endpoint exists.
Rate limits use the platform registry (athena.chat / athena.tool /
athena.high_risk). Provider failures surface as provider-neutral errors.
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit_dependency
from app.db.session import get_db
from app.models.athena import AiUsageLog
from app.models.identity import User
from app.schemas.athena import (
    AthenaConfirmOut,
    AthenaConfirmRequest,
    AthenaMessageOut,
    AthenaMessageRequest,
    AthenaSessionCreate,
    AthenaSessionOut,
    AthenaToolOut,
)
from app.services import athena as athena_service
from app.services.athena_tools import tools_for_modes

router = APIRouter(prefix="/athena", tags=["athena"])


def _limiters(request: Request):
    return getattr(request.app.state, "rate_limiters", None)


@router.get("/modes", response_model=List[str])
def athena_modes(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[str]:
    """Modes available to the authenticated user (server-derived, never client-declared)."""
    return athena_service.available_modes(db, user)


@router.get("/tools", response_model=List[AthenaToolOut])
def athena_tools(
    mode: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[dict]:
    """Declared tool surface for one mode (metadata only; authorization is
    enforced per invocation in application code)."""
    return tools_for_modes({mode})


@router.post(
    "/session",
    response_model=AthenaSessionOut,
    dependencies=[Depends(rate_limit_dependency("athena.chat"))],
)
def create_athena_session(
    body: AthenaSessionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    session = athena_service.create_session(
        db,
        user,
        body.mode,
        purpose=body.purpose,
        organization_id=body.organization_id,
    )
    return {
        "session_id": session.id,
        "mode": session.mode,
        "purpose": session.purpose,
        "organization_id": session.organization_id,
        "status": session.status,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }


@router.post(
    "/message",
    response_model=AthenaMessageOut,
    dependencies=[Depends(rate_limit_dependency("athena.chat"))],
)
def athena_message(
    body: AthenaMessageRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    session = athena_service.get_owned_session(db, user, body.session_id)
    return athena_service.chat(
        db,
        user,
        session,
        body.message,
        limiters=_limiters(request),
    )


@router.post(
    "/confirm",
    response_model=AthenaConfirmOut,
    dependencies=[Depends(rate_limit_dependency("athena.high_risk"))],
)
def athena_confirm(
    body: AthenaConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return athena_service.confirm_action(
        db, user, body.confirmation_id, body.approve, limiters=_limiters(request)
    )


@router.get(
    "/confirmations",
    response_model=List[dict],
    dependencies=[Depends(rate_limit_dependency("athena.tool"))],
)
def pending_confirmations(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> List[dict]:
    return athena_service.list_pending_confirmations(db, user, session_id)


@router.post("/session/{session_id}/close", response_model=AthenaSessionOut)
def close_athena_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    session = athena_service.close_session(db, user, session_id)
    return {
        "session_id": session.id,
        "mode": session.mode,
        "purpose": session.purpose,
        "organization_id": session.organization_id,
        "status": session.status,
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }


@router.get("/usage", response_model=List[dict])
def athena_usage(
    limit: int = 25,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    """The caller's own recent AI usage (their own rows only)."""
    rows = db.scalars(
        select(AiUsageLog)
        .where(AiUsageLog.user_id == user.id)
        .order_by(AiUsageLog.created_at.desc())
        .limit(min(limit, 100))
    ).all()
    return [
        {
            "feature": r.feature,
            "status": r.status,
            "total_tokens": r.total_tokens,
            "estimated_cost": r.estimated_cost,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]