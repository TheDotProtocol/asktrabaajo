"""/api/v1/enforcement — Moderator Enforcement + Appeals (Phase 11).

Boundaries enforced here and in ``services.enforcement``:

- Proposing, approving, rejecting, revoking and deciding are PLATFORM-scope
  operations gated by granular ``enforcement.*`` / ``appeals.*`` permissions
  (``require_platform_permission`` — company/government memberships never
  satisfy them). Auditors stay read-only; moderators see enforcement context
  but hold no enforcement powers.
- Severe action types require creator != approver (separation of duties).
- An enforcement target may submit/withdraw an appeal against THEIR OWN
  eligible action only; the appellant can never review or decide their own
  appeal. Cross-tenant UUID knowledge changes nothing — every read re-checks
  the caller's relationship to the resource.
- Listings/detail carry lifecycle metadata, controlled reason codes and
  sanitized notes. Free-form sensitive material (report bodies, private
  communications, Work ID content) never appears here.
- Derived platform state (active | restricted | suspended) is deterministic
  and scheduler-free; ``/state/me`` discloses only the caller's own state.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_suspended_user
from app.db.session import get_db
from app.models.audit import AuditLogEntry
from app.models.enforcement import Appeal, EnforcementAction
from app.models.identity import User
from app.schemas.common import MessageResponse
from app.schemas.enforcement import (
    AppealAssign,
    AppealCreate,
    AppealDecide,
    AppealListOut,
    AppealOut,
    DerivedUserStateOut,
    EnforcementActionApprove,
    EnforcementActionCreate,
    EnforcementActionListOut,
    EnforcementActionOut,
    EnforcementActionReject,
    EnforcementActionRevoke,
)
from app.services import audit as audit_service
from app.services import authz
from app.services import enforcement as enforcement_service

router = APIRouter(prefix="/enforcement", tags=["enforcement"])


def _require(db: Session, user: User, permission: str) -> None:
    authz.require_platform_permission(db, user.id, permission)


def _action_audit_timeline(db: Session, action: EnforcementAction) -> list:
    rows = db.scalars(
        select(AuditLogEntry)
        .where(
            AuditLogEntry.resource_type == "enforcement_action",
            AuditLogEntry.resource_id == str(action.id),
        )
        .order_by(AuditLogEntry.created_at.asc())
    ).all()
    return [
        {
            "action": r.action,
            "result": r.result,
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "created_at": r.created_at,
            "payload": r.payload or {},
        }
        for r in rows
    ]


def _appeal_audit_timeline(db: Session, appeal: Appeal) -> list:
    rows = db.scalars(
        select(AuditLogEntry)
        .where(
            AuditLogEntry.resource_type == "appeal",
            AuditLogEntry.resource_id == str(appeal.id),
        )
        .order_by(AuditLogEntry.created_at.asc())
    ).all()
    return [
        {
            "action": r.action,
            "result": r.result,
            "actor_id": str(r.actor_id) if r.actor_id else None,
            "created_at": r.created_at,
            "payload": r.payload or {},
        }
        for r in rows
    ]


# --- enforcement actions ---------------------------------------------------------


@router.get("/actions", response_model=EnforcementActionListOut)
def list_actions(
    case_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None, max_length=20),
    action_type: Optional[str] = Query(default=None, max_length=40),
    scope: Optional[str] = Query(default=None, max_length=40),
    target_user_id: Optional[uuid.UUID] = Query(default=None),
    target_organization_id: Optional[uuid.UUID] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Governance queue of enforcement actions (``enforcement.read``)."""
    _require(db, user, "enforcement.read")
    return enforcement_service.list_actions(
        db,
        case_id=case_id,
        status=status,
        scope=scope,
        action_type=action_type,
        target_user_id=target_user_id,
        target_organization_id=target_organization_id,
        page=page,
        page_size=page_size,
    )


@router.post("/actions", response_model=EnforcementActionOut, status_code=201)
def propose_action(
    body: EnforcementActionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    action = enforcement_service.propose_action(
        db,
        actor_id=user.id,
        case_id=body.case_id,
        target_user_id=body.target_user_id,
        target_organization_id=body.target_organization_id,
        action_type=body.action_type,
        scope=body.scope,
        reason_code=body.reason_code,
        note=body.note,
        effective_at=body.effective_at,
        expires_at=body.expires_at,
    )
    out = enforcement_service.action_out(action)
    out["audit"] = _action_audit_timeline(db, action)
    return out


@router.get("/actions/{action_id}", response_model=EnforcementActionOut)
def action_detail(
    action_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require(db, user, "enforcement.read")
    action = db.get(EnforcementAction, action_id)
    if action is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Enforcement action not found.")
    out = enforcement_service.action_out(action)
    out["audit"] = _action_audit_timeline(db, action)
    return out


@router.post("/actions/{action_id}/approve", response_model=EnforcementActionOut)
def approve_action(
    action_id: uuid.UUID,
    body: EnforcementActionApprove,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    action = enforcement_service.approve_action(
        db, actor_id=user.id, action_id=action_id, approval_note=body.approval_note
    )
    out = enforcement_service.action_out(action)
    out["audit"] = _action_audit_timeline(db, action)
    return out


@router.post("/actions/{action_id}/reject", response_model=EnforcementActionOut)
def reject_action(
    action_id: uuid.UUID,
    body: EnforcementActionReject,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    action = enforcement_service.reject_action(
        db, actor_id=user.id, action_id=action_id, rejection_note=body.rejection_note
    )
    out = enforcement_service.action_out(action)
    out["audit"] = _action_audit_timeline(db, action)
    return out


@router.post("/actions/{action_id}/revoke", response_model=EnforcementActionOut)
def revoke_action(
    action_id: uuid.UUID,
    body: EnforcementActionRevoke,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    action = enforcement_service.revoke_action(
        db, actor_id=user.id, action_id=action_id, revoke_note=body.revoke_note
    )
    out = enforcement_service.action_out(action)
    out["audit"] = _action_audit_timeline(db, action)
    return out


@router.get("/state/me", response_model=DerivedUserStateOut)
def my_platform_state(
    user: User = Depends(get_suspended_user),
    db: Session = Depends(get_db),
) -> dict:
    """The caller's own derived platform state (active|restricted|suspended).

    Reconciliation is lazy maintenance: when a lapsed window releases the
    target, the identity write is persisted here so the next request passes
    the default auth gate.
    """
    state = enforcement_service.derived_user_state(db, user.id)
    db.commit()
    return state


# --- appeals ----------------------------------------------------------------------


@router.post("/appeals", response_model=AppealOut, status_code=201)
def submit_appeal(
    body: AppealCreate,
    user: User = Depends(get_suspended_user),
    db: Session = Depends(get_db),
) -> dict:
    """Self-service appeal by the enforcement target (or an org admin)."""
    appeal = enforcement_service.submit_appeal(
        db,
        appellant_id=user.id,
        enforcement_action_id=body.enforcement_action_id,
        reason_code=body.reason_code,
        statement=body.statement,
    )
    out = enforcement_service.appeal_out(appeal, include_internal=False)
    out["audit"] = _appeal_audit_timeline(db, appeal)
    return out


@router.get("/appeals/me", response_model=AppealListOut)
def my_appeals(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_suspended_user),
    db: Session = Depends(get_db),
) -> dict:
    """The caller's own appeals — appellant-visible fields only."""
    result = enforcement_service.list_appeals(
        db, appellant_user_id=user.id, page=page, page_size=page_size
    )
    for item in result["items"]:
        item.pop("review_note", None)
    return result


@router.get("/appeals", response_model=AppealListOut)
def list_appeals(
    status: Optional[str] = Query(default=None, max_length=20),
    decision: Optional[str] = Query(default=None, max_length=20),
    assigned_to_me: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Governance appeals queue (``appeals.read``). Internal notes included."""
    _require(db, user, "appeals.read")
    return enforcement_service.list_appeals(
        db,
        status=status,
        decision=decision,
        assigned_reviewer_id=user.id if assigned_to_me else None,
        page=page,
        page_size=page_size,
    )


@router.get("/appeals/{appeal_id}", response_model=AppealOut)
def appeal_detail(
    appeal_id: uuid.UUID,
    user: User = Depends(get_suspended_user),
    db: Session = Depends(get_db),
) -> dict:
    """Appellant sees their own appeal (never internal notes); governance
    users with ``appeals.read`` see the review copy."""
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        from app.core.errors import NotFoundError

        raise NotFoundError("Appeal not found.")
    if appeal.appellant_user_id == user.id:
        out = enforcement_service.appeal_out(appeal, include_internal=False)
    else:
        authz.require_platform_permission(db, user.id, "appeals.read")
        out = enforcement_service.appeal_out(appeal, include_internal=True)
    out["audit"] = _appeal_audit_timeline(db, appeal)
    return out


@router.post("/appeals/{appeal_id}/withdraw", response_model=AppealOut)
def withdraw_appeal(
    appeal_id: uuid.UUID,
    user: User = Depends(get_suspended_user),
    db: Session = Depends(get_db),
) -> dict:
    appeal = enforcement_service.withdraw_appeal(
        db, appellant_id=user.id, appeal_id=appeal_id
    )
    out = enforcement_service.appeal_out(appeal, include_internal=False)
    out["audit"] = _appeal_audit_timeline(db, appeal)
    return out


@router.post("/appeals/{appeal_id}/assign", response_model=AppealOut)
def assign_appeal(
    appeal_id: uuid.UUID,
    body: AppealAssign,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require(db, user, "appeals.manage")
    appeal = enforcement_service.assign_appeal(
        db, actor_id=user.id, appeal_id=appeal_id, reviewer_id=body.reviewer_id
    )
    out = enforcement_service.appeal_out(appeal, include_internal=True)
    out["audit"] = _appeal_audit_timeline(db, appeal)
    return out


@router.post("/appeals/{appeal_id}/review", response_model=AppealOut)
def begin_review(
    appeal_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require(db, user, "appeals.manage")
    appeal = enforcement_service.begin_review(
        db, actor_id=user.id, appeal_id=appeal_id
    )
    out = enforcement_service.appeal_out(appeal, include_internal=True)
    out["audit"] = _appeal_audit_timeline(db, appeal)
    return out


@router.post("/appeals/{appeal_id}/decide", response_model=AppealOut)
def decide_appeal(
    appeal_id: uuid.UUID,
    body: AppealDecide,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    appeal = enforcement_service.decide_appeal(
        db,
        actor_id=user.id,
        appeal_id=appeal_id,
        decision=body.decision,
        decision_note=body.decision_note,
        review_note=body.review_note,
    )
    out = enforcement_service.appeal_out(appeal, include_internal=True)
    out["audit"] = _appeal_audit_timeline(db, appeal)
    return out
