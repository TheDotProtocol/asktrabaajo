"""Moderator enforcement + appeals service (Phase 11).

Architecture: a governance CASE is never itself an enforcement action.

    Report -> Case -> Investigation -> Decision
    -> ENFORCEMENT ACTION -> Audit -> Appeal -> Final resolution

- Actions are explicit, granular rows (type + scope + reason code are
  controlled values). They are NEVER a generic "admin can do everything"
  record. Severe action types (account/organization restriction, suspension,
  reinstatement) require an APPROVAL SEPARATION: creator != approver.
- Correctness never depends on a background scheduler:
    * ACTIVE/EXPIRED is derived from ``effective_at``/``expires_at``.
    * ``reconcile_user``/``reconcile_org`` lazily sync identity status
      (and invalidate sessions on suspension) whenever a gate runs.
  An approved action with a future effective_at becomes effective the first
  time a gate/auth path checks it — deterministically and safely.
- Appeals let an eligible enforcement target contest an action. Decisions
  never mutate the original silently: an accepted/partial decision creates a
  NEW superseding reinstatement action through the audited lifecycle and
  revokes the original with an explicit note. The deciding moderator may
  create-and-activate a reinstatement (a rights-RESTORING action); the risky
  direction (restrict/suspend) always needs a second approver.
- Reason codes are controlled; free-form sensitive narratives never enter
  audit/event payloads or out-of-band notifications. Bounded sanitized notes
  are allowed; internal review notes are never exposed to the appellant.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import (
    ConflictError,
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.timeutil import utc_now_naive
from app.models.audit import AuditLogEntry
from app.models.enforcement import Appeal, EnforcementAction
from app.models.enums import (
    APPEAL_DECISION_ACCEPTED,
    APPEAL_DECISION_PARTIALLY_GRANTED,
    APPEAL_DECISION_REJECTED,
    APPEAL_DECISIONS,
    APPEAL_REASON_CODES,
    APPEAL_STATUS_ASSIGNED,
    APPEAL_STATUS_DECIDED,
    APPEAL_STATUS_SUBMITTED,
    APPEAL_STATUS_UNDER_REVIEW,
    APPEAL_STATUS_WITHDRAWN,
    APPEAL_STATUSES,
    ENFORCEMENT_APPROVAL_REQUIRED_TYPES,
    ENFORCEMENT_REASON_CODES,
    ENFORCEMENT_SCOPES,
    ENFORCEMENT_STATUS_ACTIVE,
    ENFORCEMENT_STATUS_APPROVED,
    ENFORCEMENT_STATUS_EXPIRED,
    ENFORCEMENT_STATUS_PROPOSED,
    ENFORCEMENT_STATUS_REJECTED,
    ENFORCEMENT_STATUS_REVOKED,
    ENFORCEMENT_TYPES,
    ENFORCEMENT_TYPE_REINSTATEMENT,
    ENFORCEMENT_TYPE_SUSPENSION,
    ORG_STATUS_ACTIVE,
    ORG_STATUS_SUSPENDED,
    PERMISSION_APPEALS_DECIDE,
    PERMISSION_APPEALS_MANAGE,
    PERMISSION_ENFORCEMENT_APPROVE,
    PERMISSION_ENFORCEMENT_CREATE,
    PERMISSION_ENFORCEMENT_REVOKE,
    USER_STATUS_ACTIVE,
    USER_STATUS_SUSPENDED,
)
from app.models.governance import GovernanceReport
from app.models.identity import RefreshToken, User
from app.models.tenancy import Membership, Organization, Role
from app.services import audit as audit_service
from app.services import events as events_service
from app.services import notifications as notifications_service

# --- constants -----------------------------------------------------------------

_APPEALABLE_STORED_STATUSES = {
    ENFORCEMENT_STATUS_ACTIVE,
    ENFORCEMENT_STATUS_APPROVED,
    ENFORCEMENT_STATUS_REVOKED,
    ENFORCEMENT_STATUS_EXPIRED,
}
_OPEN_APPEAL_STATUSES = {
    APPEAL_STATUS_SUBMITTED,
    APPEAL_STATUS_ASSIGNED,
    APPEAL_STATUS_UNDER_REVIEW,
}
# Scopes whose derived-active restrictions must block which product areas.
_COMM_SCOPES = {"communications", "account", "platform_access"}
_APPLICATION_SCOPES = {"applications", "account", "platform_access"}
_MAX_NOTE = 500
_MAX_STATEMENT = 4000
_MAX_DECISION_NOTE = 1000
REVIEW_WINDOW_DAYS = 30  # an enforcement may be appealed within this window


def _now() -> datetime:
    return utc_now_naive()


def _coerce(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize a stored timestamp to naive UTC for comparisons.

    SQLite returns naive values; PostgreSQL (timestamptz) returns tz-aware
    values. Comparisons in this module always run in naive UTC, so stored
    values are normalized first — deterministic on both dialects.
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _action(db: Session, action_id: uuid.UUID) -> EnforcementAction:
    action = db.get(EnforcementAction, action_id)
    if action is None:
        raise NotFoundError("Enforcement action not found.")
    return action


def _appeal(db: Session, appeal_id: uuid.UUID) -> Appeal:
    appeal = db.get(Appeal, appeal_id)
    if appeal is None:
        raise NotFoundError("Appeal not found.")
    return appeal


def _user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def _require_platform(db: Session, user_id: uuid.UUID, permission: str) -> None:
    from app.services import authz

    authz.require_platform_permission(db, user_id, permission)


# --- deterministic lifecycle ---------------------------------------------------

def is_in_effect(action: EnforcementAction, now: Optional[datetime] = None) -> bool:
    """Scheduler-free: is this action currently binding on its target?

    Approved-but-not-yet-started actions are in effect the moment their
    window opens; expired windows are not in effect even if no worker has
    flipped the stored row.
    """
    now = now or _now()
    if action.status not in (ENFORCEMENT_STATUS_ACTIVE, ENFORCEMENT_STATUS_APPROVED):
        return False
    if _coerce(action.effective_at) > now:
        return False
    if action.expires_at is not None and _coerce(action.expires_at) <= now:
        return False
    return True


def derive_action_state(action: EnforcementAction, now: Optional[datetime] = None) -> str:
    """The truthful display state (active/expired vs stored lifecycle state)."""
    now = now or _now()
    if action.status in (ENFORCEMENT_STATUS_ACTIVE, ENFORCEMENT_STATUS_APPROVED):
        if _coerce(action.effective_at) > now:
            return ENFORCEMENT_STATUS_APPROVED  # scheduled, not yet started
        if action.expires_at is not None and _coerce(action.expires_at) <= now:
            return ENFORCEMENT_STATUS_EXPIRED
        return ENFORCEMENT_STATUS_ACTIVE
    return action.status


def _derived_active_for_target(
    db: Session,
    *,
    user_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    action_types: Optional[set] = None,
    scopes: Optional[set] = None,
) -> list:
    """Derived-active actions matching a target (user and/or organization)."""
    conditions = []
    if user_id is not None:
        conditions.append(EnforcementAction.target_user_id == user_id)
    if organization_id is not None:
        conditions.append(EnforcementAction.target_organization_id == organization_id)
    if not conditions:
        return []
    query = select(EnforcementAction).where(
        EnforcementAction.status.in_(
            [ENFORCEMENT_STATUS_ACTIVE, ENFORCEMENT_STATUS_APPROVED]
        ),
        or_(*conditions),
    )
    actions = db.scalars(query).all()
    now = _now()
    out = []
    for action in actions:
        if action_types is not None and action.action_type not in action_types:
            continue
        if scopes is not None and action.scope not in scopes:
            continue
        if is_in_effect(action, now):
            out.append(action)
    return out


# --- identity reconciliation (lazy, scheduler-free) -----------------------------

def _suspend_user_side_effects(db: Session, user: User) -> None:
    """Suspension invalidates the identity gate + every existing session."""
    user.status = USER_STATUS_SUSPENDED
    user.token_version = (user.token_version or 0) + 1
    db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id)
        .where(RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def _restore_user_side_effects(db: Session, user: User) -> None:
    """Remove a stale suspension from identity (sessions re-issued on login)."""
    user.status = USER_STATUS_ACTIVE


def reconcile_user(db: Session, user: User) -> User:
    """Lazily sync identity state with derived enforcement state.

    Runs on auth paths and product gates. Guarantees:

    - A suspension whose window opened (or lapsed) without a scheduler is
      honored/cleared on the next check.
    - A stale ``suspended`` identity row with no active suspension is
      restored to active (sessions are short-lived; the user re-authenticates).
    - Expired stored rows are flipped so the UI never shows phantom ACTIVE.
    """
    active_suspensions = _derived_active_for_target(
        db, user_id=user.id, action_types={ENFORCEMENT_TYPE_SUSPENSION}
    )
    if active_suspensions:
        if user.status != USER_STATUS_SUSPENDED:
            _suspend_user_side_effects(db, user)
    elif user.status == USER_STATUS_SUSPENDED:
        _restore_user_side_effects(db, user)
    # Flip phantom stored ACTIVE rows that have lapsed.
    now = _now()
    stale = db.scalars(
        select(EnforcementAction).where(
            EnforcementAction.status == ENFORCEMENT_STATUS_ACTIVE,
            EnforcementAction.target_user_id == user.id,
            EnforcementAction.expires_at.is_not(None),
        )
    ).all()
    for action in stale:
        if _coerce(action.expires_at) <= now:
            action.status = ENFORCEMENT_STATUS_EXPIRED
    return user


def reconcile_org(db: Session, org: Organization) -> Organization:
    active_suspensions = _derived_active_for_target(
        db,
        organization_id=org.id,
        action_types={ENFORCEMENT_TYPE_SUSPENSION},
    )
    if active_suspensions:
        if org.status != ORG_STATUS_SUSPENDED:
            org.status = ORG_STATUS_SUSPENDED
    elif org.status == ORG_STATUS_SUSPENDED:
        org.status = ORG_STATUS_ACTIVE
    now = _now()
    stale = db.scalars(
        select(EnforcementAction).where(
            EnforcementAction.status == ENFORCEMENT_STATUS_ACTIVE,
            EnforcementAction.target_organization_id == org.id,
            EnforcementAction.expires_at.is_not(None),
        )
    ).all()
    for action in stale:
        if _coerce(action.expires_at) <= now:
            action.status = ENFORCEMENT_STATUS_EXPIRED
    return org


# --- product gates (route/service boundaries) -----------------------------------

def _deny_restricted() -> None:
    # Generic message: no detail about which restriction is active.
    raise PermissionDeniedError(
        "Your account currently has platform restrictions in effect.",
        details={"code": "account_restricted"},
    )


def check_communication_allowed(db: Session, user_id: uuid.UUID) -> None:
    """Gate for outreach creation + conversation messages (both sides)."""
    reconcile_user(db, _user(db, user_id))
    user = _user(db, user_id)
    if user.status == USER_STATUS_SUSPENDED:
        _deny_restricted()
    hits = _derived_active_for_target(
        db, user_id=user_id, scopes=_COMM_SCOPES
    )
    if hits:
        _deny_restricted()


def check_application_allowed(db: Session, user_id: uuid.UUID) -> None:
    reconcile_user(db, _user(db, user_id))
    user = _user(db, user_id)
    if user.status == USER_STATUS_SUSPENDED:
        _deny_restricted()
    hits = _derived_active_for_target(
        db, user_id=user_id, scopes=_APPLICATION_SCOPES
    )
    if hits:
        _deny_restricted()


def check_org_operational(db: Session, organization_id: uuid.UUID) -> None:
    """Gate for employer-side publishing/operational actions."""
    org = db.get(Organization, organization_id)
    if org is None:
        raise NotFoundError("Organization not found.")
    reconcile_org(db, org)
    if org.status == ORG_STATUS_SUSPENDED:
        _deny_restricted()


# --- action creation / lifecycle -------------------------------------------------

_TYPE_SCOPE_GUIDANCE: dict = {
    "warning": {"account", "communications", "applications", "governance_participation"},
    "content_restriction": {"communications", "applications", "governance_participation"},
    "communication_restriction": {"communications", "account"},
    "account_restriction": {"account", "applications", "platform_access"},
    "organization_restriction": {"company_organization", "platform_access"},
    "suspension": {"account", "platform_access", "company_organization"},
    "reinstatement": {"account", "platform_access", "company_organization", "communications", "applications"},
}


def _validate_target_and_scope(
    action_type: str, scope: str, target_user_id, target_organization_id
) -> None:
    allowed = _TYPE_SCOPE_GUIDANCE.get(action_type, set())
    if scope not in allowed:
        raise InvalidInputError(
            f"Scope '{scope}' is not valid for action type '{action_type}'."
        )
    user_scopes = {"account", "applications", "communications"}
    if scope in user_scopes and target_user_id is None:
        raise InvalidInputError(
            f"Scope '{scope}' requires a target user."
        )
    if scope == "company_organization" and target_organization_id is None:
        raise InvalidInputError(
            "An organization-scoped action requires a target organization."
        )
    if scope == "platform_access" and not (
        target_user_id or target_organization_id
    ):
        raise InvalidInputError(
            "A platform-access action requires a target user or organization."
        )


def propose_action(
    db: Session,
    *,
    actor_id: uuid.UUID,
    case_id: Optional[uuid.UUID],
    target_user_id: Optional[uuid.UUID],
    target_organization_id: Optional[uuid.UUID],
    action_type: str,
    scope: str,
    reason_code: str,
    note: Optional[str],
    effective_at: datetime,
    expires_at: Optional[datetime],
) -> EnforcementAction:
    """Propose a controlled enforcement action (``enforcement.create``)."""
    _require_platform(db, actor_id, PERMISSION_ENFORCEMENT_CREATE)
    if action_type not in ENFORCEMENT_TYPES:
        raise InvalidInputError(f"Unknown action type '{action_type}'.")
    if scope not in ENFORCEMENT_SCOPES:
        raise InvalidInputError(f"Unknown scope '{scope}'.")
    if reason_code not in ENFORCEMENT_REASON_CODES:
        raise InvalidInputError(f"Unknown reason code '{reason_code}'.")
    _validate_target_and_scope(
        action_type, scope, target_user_id, target_organization_id
    )
    if case_id is not None and db.get(GovernanceReport, case_id) is None:
        raise InvalidInputError("Referenced governance case does not exist.")
    if target_user_id is not None and db.get(User, target_user_id) is None:
        raise InvalidInputError("Referenced target user does not exist.")
    if target_organization_id is not None and db.get(
        Organization, target_organization_id
    ) is None:
        raise InvalidInputError("Referenced target organization does not exist.")
    if target_user_id == actor_id:
        raise InvalidInputError("An actor cannot target their own account.")
    now = _now()
    if note and len(note) > _MAX_NOTE:
        raise InvalidInputError("Note is too long.")
    action = EnforcementAction(
        governance_case_id=case_id,
        target_user_id=target_user_id,
        target_organization_id=target_organization_id,
        action_type=action_type,
        scope=scope,
        reason_code=reason_code,
        note=note or None,
        status=ENFORCEMENT_STATUS_PROPOSED,
        created_by=actor_id,
        effective_at=effective_at,
        expires_at=expires_at,
    )
    db.add(action)
    db.flush()
    audit_service.record(
        db,
        actor_id=actor_id,
        action="enforcement.action.proposed",
        resource_type="enforcement_action",
        resource_id=action.id,
        metadata={
            "action_type": action_type,
            "scope": scope,
            "reason_code": reason_code,
            "case_id": str(case_id) if case_id else None,
            "target_user_id": str(target_user_id) if target_user_id else None,
            "target_organization_id": str(target_organization_id)
            if target_organization_id
            else None,
        },
    )
    db.commit()
    db.refresh(action)
    return action


def _activate_action(db: Session, action: EnforcementAction, now: datetime) -> None:
    """Apply activation side effects (identity writes). Notifications and
    events are queued by the caller so everything commits atomically."""
    action.status = ENFORCEMENT_STATUS_ACTIVE
    action.activated_at = now
    if action.action_type == ENFORCEMENT_TYPE_SUSPENSION:
        if action.target_user_id is not None:
            user = db.get(User, action.target_user_id)
            if user is not None and user.status != USER_STATUS_SUSPENDED:
                _suspend_user_side_effects(db, user)
        if action.target_organization_id is not None:
            org = db.get(Organization, action.target_organization_id)
            if org is not None and org.status != ORG_STATUS_SUSPENDED:
                org.status = ORG_STATUS_SUSPENDED


def _queue_target_notification(
    db: Session,
    action: EnforcementAction,
    *,
    title: str,
    event_type: str,
    actor_id: uuid.UUID,
) -> None:
    """Queue in-app notification + metadata-only event for the target user.

    Called with everything else already queued: ``notify`` performs the
    terminating commit for the whole operation (the established pattern).
    """
    if action.target_user_id is None:
        return
    events_service.emit(
        db,
        event_type=event_type,
        resource_type="enforcement_action",
        resource_id=action.id,
        recipient_user_id=action.target_user_id,
        actor_user_id=actor_id,
        payload={
            "action_type": action.action_type,
            "scope": action.scope,
            "reason_code": action.reason_code,
        },
    )
    notifications_service.notify(
        db,
        action.target_user_id,
        title,
        "Sign in to AskTrabaajo for details.",
        kind="governance",
    )


def approve_action(
    db: Session,
    *,
    actor_id: uuid.UUID,
    action_id: uuid.UUID,
    approval_note: Optional[str],
) -> EnforcementAction:
    """Approve (and immediately activate, when the window is open) an action.

    Requires ``enforcement.approve``. For approval-required action types the
    approver MUST differ from the creator (separation of duties).
    """
    _require_platform(db, actor_id, PERMISSION_ENFORCEMENT_APPROVE)
    action = _action(db, action_id)
    if action.status != ENFORCEMENT_STATUS_PROPOSED:
        raise ConflictError("Only proposed actions can be approved.")
    if action.action_type in ENFORCEMENT_APPROVAL_REQUIRED_TYPES:
        if action.created_by == actor_id:
            raise PermissionDeniedError(
                "This action type requires approval by someone other than its creator.",
                details={"code": "approval_separation_required"},
            )
    if action.target_user_id == actor_id:
        raise PermissionDeniedError("An actor cannot approve actions on their own account.")
    if approval_note and len(approval_note) > _MAX_NOTE:
        raise InvalidInputError("Approval note is too long.")
    action.status = ENFORCEMENT_STATUS_APPROVED
    action.approved_by = actor_id
    action.approval_note = approval_note or None
    now = _now()
    activated = False
    window_open = _coerce(action.effective_at) <= now and (
        action.expires_at is None or _coerce(action.expires_at) > now
    )
    if window_open:
        _activate_action(db, action, now)
        activated = True
    audit_service.record(
        db,
        actor_id=actor_id,
        action="enforcement.action.approved",
        resource_type="enforcement_action",
        resource_id=action.id,
        metadata={
            "action_type": action.action_type,
            "activated": activated,
        },
    )
    if activated:
        _queue_target_notification(
            db,
            action,
            title="A platform action has been applied to your account",
            event_type="enforcement.action.activated",
            actor_id=actor_id,
        )
    db.commit()
    db.refresh(action)
    return action


def reject_action(
    db: Session,
    *,
    actor_id: uuid.UUID,
    action_id: uuid.UUID,
    rejection_note: Optional[str],
) -> EnforcementAction:
    _require_platform(db, actor_id, PERMISSION_ENFORCEMENT_APPROVE)
    action = _action(db, action_id)
    if action.status != ENFORCEMENT_STATUS_PROPOSED:
        raise ConflictError("Only proposed actions can be rejected.")
    if rejection_note and len(rejection_note) > _MAX_NOTE:
        raise InvalidInputError("Rejection note is too long.")
    action.status = ENFORCEMENT_STATUS_REJECTED
    action.rejected_by = actor_id
    action.rejection_note = rejection_note or None
    audit_service.record(
        db,
        actor_id=actor_id,
        action="enforcement.action.rejected",
        resource_type="enforcement_action",
        resource_id=action.id,
        metadata={"action_type": action.action_type},
    )
    db.commit()
    db.refresh(action)
    return action


def revoke_action(
    db: Session,
    *,
    actor_id: uuid.UUID,
    action_id: uuid.UUID,
    revoke_note: Optional[str],
) -> EnforcementAction:
    """Revoke an approved/active action (``enforcement.revoke``).

    A revoked suspension immediately releases the target's identity gate
    unless another active suspension covers them.
    """
    _require_platform(db, actor_id, PERMISSION_ENFORCEMENT_REVOKE)
    action = _action(db, action_id)
    if action.status not in (
        ENFORCEMENT_STATUS_APPROVED,
        ENFORCEMENT_STATUS_ACTIVE,
    ):
        raise ConflictError("Only approved/active actions can be revoked.")
    if revoke_note and len(revoke_note) > _MAX_NOTE:
        raise InvalidInputError("Revoke note is too long.")
    now = _now()
    action.status = ENFORCEMENT_STATUS_REVOKED
    action.revoked_by = actor_id
    action.revoke_note = revoke_note or None
    action.revoked_at = now
    if (
        action.action_type == ENFORCEMENT_TYPE_SUSPENSION
        and action.target_user_id is not None
    ):
        user = db.get(User, action.target_user_id)
        if user is not None:
            others = _derived_active_for_target(
                db, user_id=user.id, action_types={ENFORCEMENT_TYPE_SUSPENSION}
            )
            if not others:
                user.status = USER_STATUS_ACTIVE
    audit_service.record(
        db,
        actor_id=actor_id,
        action="enforcement.action.revoked",
        resource_type="enforcement_action",
        resource_id=action.id,
        metadata={"action_type": action.action_type},
    )
    _queue_target_notification(
        db,
        action,
        title="A platform action on your account has been lifted",
        event_type="enforcement.action.revoked",
        actor_id=actor_id,
    )
    db.commit()
    db.refresh(action)
    return action


def action_timeline(db: Session, action: EnforcementAction) -> list:
    """Audit rows referencing this action (never payload bodies)."""
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


# --- derived platform state ------------------------------------------------------

def derived_user_state(db: Session, user_id: uuid.UUID) -> dict:
    """Derived state for a target user (active | restricted | suspended)."""
    user = _user(db, user_id)
    reconcile_user(db, user)
    active = _derived_active_for_target(db, user_id=user_id)
    suspensions = [a for a in active if a.action_type == ENFORCEMENT_TYPE_SUSPENSION]
    if suspensions or user.status == USER_STATUS_SUSPENDED:
        state = "suspended"
    elif active:
        state = "restricted"
    else:
        state = "active"
    return {
        "user_id": str(user_id),
        "state": state,
        "active_restrictions": [
            {
                "id": str(a.id),
                "action_type": a.action_type,
                "scope": a.scope,
                "reason_code": a.reason_code,
                "expires_at": a.expires_at,
            }
            for a in active
        ],
        "derived_at": _now(),
    }


# --- appeals ----------------------------------------------------------------------

def _is_org_appellant(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == org_id,
        )
    )
    if membership is None:
        return False
    role = db.get(Role, membership.role_code)
    return role is not None and role.code in {"org_admin", "super_admin"}


def _appeal_eligible(db: Session, appellant_id: uuid.UUID, action: EnforcementAction) -> bool:
    """The appellant is the target (or an org admin of the target org)."""
    if action.target_user_id == appellant_id:
        return True
    if (
        action.target_organization_id is not None
        and action.scope in {"company_organization", "platform_access"}
    ):
        return _is_org_appellant(db, appellant_id, action.target_organization_id)
    return False


def submit_appeal(
    db: Session,
    *,
    appellant_id: uuid.UUID,
    enforcement_action_id: uuid.UUID,
    reason_code: str,
    statement: str,
) -> Appeal:
    """Self-service appeal by the enforcement target (or org admin)."""
    action = _action(db, enforcement_action_id)
    if action.status not in _APPEALABLE_STORED_STATUSES:
        raise InvalidInputError(
            "This action cannot be appealed in its current state."
        )
    if not _appeal_eligible(db, appellant_id, action):
        raise PermissionDeniedError("You are not eligible to appeal this action.")
    # Appeal window is REVIEW_WINDOW_DAYS from the action's effective start
    # or from revocation/expiry — a bounded, deterministic policy.
    now = _now()
    anchor = _coerce(action.activated_at) or _coerce(action.effective_at) or now
    if now - anchor > timedelta(days=REVIEW_WINDOW_DAYS):
        raise InvalidInputError("This action is outside the appeal window.")
    open_existing = db.scalar(
        select(Appeal).where(
            Appeal.enforcement_action_id == enforcement_action_id,
            Appeal.appellant_user_id == appellant_id,
            Appeal.status.in_(_OPEN_APPEAL_STATUSES),
        )
    )
    if open_existing is not None:
        raise ConflictError("An appeal for this action is already under review.")
    if reason_code not in APPEAL_REASON_CODES:
        raise InvalidInputError(f"Unknown appeal reason code '{reason_code}'.")
    statement = (statement or "").strip()
    if not statement or len(statement) > _MAX_STATEMENT:
        raise InvalidInputError("A statement between 1 and 4000 characters is required.")
    appeal = Appeal(
        enforcement_action_id=enforcement_action_id,
        appellant_user_id=appellant_id,
        reason_code=reason_code,
        statement=statement,
        status=APPEAL_STATUS_SUBMITTED,
    )
    db.add(appeal)
    db.flush()
    audit_service.record(
        db,
        actor_id=appellant_id,
        action="appeal.submitted",
        resource_type="appeal",
        resource_id=appeal.id,
        metadata={
            "enforcement_action_id": str(enforcement_action_id),
            "reason_code": reason_code,
        },
    )
    db.commit()
    db.refresh(appeal)
    return appeal


def assign_appeal(
    db: Session,
    *,
    actor_id: uuid.UUID,
    appeal_id: uuid.UUID,
    reviewer_id: uuid.UUID,
) -> Appeal:
    _require_platform(db, actor_id, PERMISSION_APPEALS_MANAGE)
    appeal = _appeal(db, appeal_id)
    if appeal.status not in (
        APPEAL_STATUS_SUBMITTED,
        APPEAL_STATUS_ASSIGNED,
        APPEAL_STATUS_UNDER_REVIEW,
    ):
        raise ConflictError("This appeal can no longer be assigned.")
    if reviewer_id == appeal.appellant_user_id:
        raise InvalidInputError(
            "The appellant cannot review their own appeal."
        )
    from app.services import authz

    if not authz.has_platform_permission(db, reviewer_id, PERMISSION_APPEALS_DECIDE) and not authz.has_platform_permission(
        db, reviewer_id, PERMISSION_APPEALS_MANAGE
    ):
        raise InvalidInputError(
            "The reviewer must hold appeals.decide or appeals.manage."
        )
    appeal.assigned_reviewer_id = reviewer_id
    appeal.status = APPEAL_STATUS_ASSIGNED
    audit_service.record(
        db,
        actor_id=actor_id,
        action="appeal.assigned",
        resource_type="appeal",
        resource_id=appeal.id,
        metadata={"reviewer_id": str(reviewer_id)},
    )
    events_service.emit(
        db,
        event_type="appeal.assigned",
        resource_type="appeal",
        resource_id=appeal.id,
        recipient_user_id=reviewer_id,
        actor_user_id=actor_id,
        payload={"appeal_id": str(appeal.id)},
    )
    db.commit()
    db.refresh(appeal)
    return appeal


def begin_review(
    db: Session, *, actor_id: uuid.UUID, appeal_id: uuid.UUID
) -> Appeal:
    _require_platform(db, actor_id, PERMISSION_APPEALS_MANAGE)
    appeal = _appeal(db, appeal_id)
    if appeal.status != APPEAL_STATUS_ASSIGNED:
        raise ConflictError("Only an assigned appeal can begin review.")
    if appeal.assigned_reviewer_id != actor_id:
        raise PermissionDeniedError(
            "Only the assigned reviewer can begin review on this appeal."
        )
    appeal.status = APPEAL_STATUS_UNDER_REVIEW
    db.commit()
    db.refresh(appeal)
    return appeal


def _create_reinstatement_from_decision(
    db: Session,
    *,
    actor_id: uuid.UUID,
    original: EnforcementAction,
    now: datetime,
) -> EnforcementAction:
    """Rights-restoring superseding action created by an appeal decision.

    The risky direction (restrict/suspend) always requires creator !=
    approver; reversal (restore access) may be executed directly by the
    deciding appeals manager — the decision itself is the approval.
    """
    replacement = EnforcementAction(
        governance_case_id=original.governance_case_id,
        target_user_id=original.target_user_id,
        target_organization_id=original.target_organization_id,
        action_type=ENFORCEMENT_TYPE_REINSTATEMENT,
        scope=(
            "company_organization"
            if original.scope == "company_organization"
            else "account"
        ),
        reason_code="other",
        note="Superseding action created by an appeal decision.",
        status=ENFORCEMENT_STATUS_APPROVED,
        created_by=actor_id,
        approved_by=actor_id,
        approval_note="Executed by appeal decision (rights-restoring).",
        supersedes_id=original.id,
        effective_at=now,
    )
    db.add(replacement)
    db.flush()
    replacement.status = ENFORCEMENT_STATUS_ACTIVE
    replacement.activated_at = now
    if original.target_user_id is not None:
        user = db.get(User, original.target_user_id)
        if user is not None:
            _restore_user_side_effects(db, user)
    if original.target_organization_id is not None:
        org = db.get(Organization, original.target_organization_id)
        if org is not None:
            org.status = ORG_STATUS_ACTIVE
    # The superseded action is revoked with an explicit note (history kept).
    original.status = ENFORCEMENT_STATUS_REVOKED
    original.revoked_by = actor_id
    original.revoked_at = now
    original.revoke_note = "Superseded by an appeal decision."
    return replacement


def decide_appeal(
    db: Session,
    *,
    actor_id: uuid.UUID,
    appeal_id: uuid.UUID,
    decision: str,
    decision_note: Optional[str],
    review_note: Optional[str],
) -> Appeal:
    """Decide an appeal (``appeals.decide``). Self-decision is impossible."""
    _require_platform(db, actor_id, PERMISSION_APPEALS_DECIDE)
    appeal = _appeal(db, appeal_id)
    if appeal.status not in (
        APPEAL_STATUS_ASSIGNED,
        APPEAL_STATUS_UNDER_REVIEW,
    ):
        raise ConflictError("Only an assigned appeal can be decided.")
    if appeal.appellant_user_id == actor_id:
        raise PermissionDeniedError("A moderator cannot decide their own appeal.")
    if appeal.assigned_reviewer_id is not None and appeal.assigned_reviewer_id != actor_id:
        # A different manager may take over only after reassignment.
        raise PermissionDeniedError(
            "This appeal is assigned to another reviewer.",
            details={"code": "appeal_assigned_elsewhere"},
        )
    if decision not in APPEAL_DECISIONS:
        raise InvalidInputError(f"Unknown appeal decision '{decision}'.")
    decision_note = (decision_note or "").strip()
    if not decision_note or len(decision_note) > _MAX_DECISION_NOTE:
        raise InvalidInputError("A decision note between 1 and 1000 characters is required.")
    now = _now()
    appeal.status = APPEAL_STATUS_DECIDED
    appeal.decided_by = actor_id
    appeal.decision = decision
    appeal.decision_note = decision_note  # appellant-visible, sanitized wording
    appeal.review_note = (review_note or "").strip() or None  # internal only
    appeal.decided_at = now

    original = _action(db, appeal.enforcement_action_id)
    superseding = None
    if decision in (APPEAL_DECISION_ACCEPTED, APPEAL_DECISION_PARTIALLY_GRANTED):
        superseding = _create_reinstatement_from_decision(
            db, actor_id=actor_id, original=original, now=now
        )
        appeal.superseding_action_id = superseding.id
        db.flush()

    events_service.emit(
        db,
        event_type="appeal.decided",
        resource_type="appeal",
        resource_id=appeal.id,
        recipient_user_id=appeal.appellant_user_id,
        actor_user_id=actor_id,
        payload={
            "decision": decision,
            "superseding_action_id": str(superseding.id)
            if superseding is not None
            else None,
        },
    )
    audit_service.record(
        db,
        actor_id=actor_id,
        action="appeal.decided",
        resource_type="appeal",
        resource_id=appeal.id,
        metadata={
            "decision": decision,
            "superseding_action_id": str(superseding.id)
            if superseding is not None
            else None,
        },
    )
    # Final terminating call (commits the whole decision atomically).
    notifications_service.notify(
        db,
        appeal.appellant_user_id,
        "Your appeal has been decided",
        "Sign in to AskTrabaajo to view the outcome.",
        kind="governance",
    )
    db.commit()
    db.refresh(appeal)
    return appeal


def withdraw_appeal(
    db: Session, *, appellant_id: uuid.UUID, appeal_id: uuid.UUID
) -> Appeal:
    appeal = _appeal(db, appeal_id)
    if appeal.appellant_user_id != appellant_id:
        raise PermissionDeniedError("Only the appellant can withdraw this appeal.")
    if appeal.status not in _OPEN_APPEAL_STATUSES:
        raise ConflictError("This appeal can no longer be withdrawn.")
    appeal.status = APPEAL_STATUS_WITHDRAWN
    appeal.withdrawn_at = _now()
    audit_service.record(
        db,
        actor_id=appellant_id,
        action="appeal.withdrawn",
        resource_type="appeal",
        resource_id=appeal.id,
        metadata={},
    )
    db.commit()
    db.refresh(appeal)
    return appeal


# --- queries ---------------------------------------------------------------------

def list_actions(
    db: Session,
    *,
    case_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    scope: Optional[str] = None,
    target_user_id: Optional[uuid.UUID] = None,
    target_organization_id: Optional[uuid.UUID] = None,
    action_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = select(EnforcementAction)
    if case_id is not None:
        query = query.where(EnforcementAction.governance_case_id == case_id)
    if scope:
        query = query.where(EnforcementAction.scope == scope)
    if target_user_id is not None:
        query = query.where(EnforcementAction.target_user_id == target_user_id)
    if target_organization_id is not None:
        query = query.where(
            EnforcementAction.target_organization_id == target_organization_id
        )
    if action_type:
        query = query.where(EnforcementAction.action_type == action_type)
    if status:
        if status == ENFORCEMENT_STATUS_EXPIRED:
            # derived: stored ACTIVE/APPROVED rows whose window has closed
            now = _now()
            rows = db.scalars(query.order_by(EnforcementAction.created_at.desc())).all()
            filtered = [a for a in rows if derive_action_state(a, now) == status]
            return _paginate_actions(db, filtered, page, page_size)
        query = query.where(EnforcementAction.status == status)
    rows = db.scalars(query.order_by(EnforcementAction.created_at.desc())).all()
    return _paginate_actions(db, list(rows), page, page_size)


def _paginate_actions(db: Session, rows: list, page: int, page_size: int) -> dict:
    total = len(rows)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    start = (page - 1) * page_size
    window = rows[start : start + page_size]
    now = _now()
    return {
        "items": [action_out(a, now) for a in window],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def action_out(action: EnforcementAction, now: Optional[datetime] = None) -> dict:
    now = now or _now()
    return {
        "id": str(action.id),
        "governance_case_id": str(action.governance_case_id)
        if action.governance_case_id
        else None,
        "target_user_id": str(action.target_user_id)
        if action.target_user_id
        else None,
        "target_organization_id": str(action.target_organization_id)
        if action.target_organization_id
        else None,
        "action_type": action.action_type,
        "scope": action.scope,
        "reason_code": action.reason_code,
        "status": derive_action_state(action, now),
        "stored_status": action.status,
        "created_by": str(action.created_by),
        "approved_by": str(action.approved_by) if action.approved_by else None,
        "effective_at": action.effective_at,
        "expires_at": action.expires_at,
        "activated_at": action.activated_at,
        "revoked_at": action.revoked_at,
        "supersedes_id": str(action.supersedes_id) if action.supersedes_id else None,
        "note": action.note,
        "created_at": action.created_at,
    }


def list_appeals(
    db: Session,
    *,
    status: Optional[str] = None,
    decision: Optional[str] = None,
    appellant_user_id: Optional[uuid.UUID] = None,
    assigned_reviewer_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    query = select(Appeal)
    if status:
        if status not in APPEAL_STATUSES:
            raise InvalidInputError(f"Unknown appeal status '{status}'.")
        query = query.where(Appeal.status == status)
    if decision:
        if decision not in APPEAL_DECISIONS:
            raise InvalidInputError(f"Unknown appeal decision '{decision}'.")
        query = query.where(Appeal.decision == decision)
    if appellant_user_id is not None:
        query = query.where(Appeal.appellant_user_id == appellant_user_id)
    if assigned_reviewer_id is not None:
        query = query.where(Appeal.assigned_reviewer_id == assigned_reviewer_id)
    rows = db.scalars(query.order_by(Appeal.created_at.desc())).all()
    total = len(rows)
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    start = (page - 1) * page_size
    # The governance queue carries the internal review note; appellant-only
    # views strip it at the API boundary.
    return {
        "items": [appeal_out(a, include_internal=True) for a in rows[start : start + page_size]],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def appeal_out(appeal: Appeal, *, include_internal: bool = False) -> dict:
    out = {
        "id": str(appeal.id),
        "enforcement_action_id": str(appeal.enforcement_action_id),
        "appellant_user_id": str(appeal.appellant_user_id),
        "reason_code": appeal.reason_code,
        "status": appeal.status,
        "assigned_reviewer_id": str(appeal.assigned_reviewer_id)
        if appeal.assigned_reviewer_id
        else None,
        "decision": appeal.decision,
        "decision_note": appeal.decision_note,
        "decided_by": str(appeal.decided_by) if appeal.decided_by else None,
        "decided_at": appeal.decided_at,
        "withdrawn_at": appeal.withdrawn_at,
        "superseding_action_id": str(appeal.superseding_action_id)
        if appeal.superseding_action_id
        else None,
        "created_at": appeal.created_at,
        "updated_at": appeal.updated_at,
    }
    # The appellant's own sanitized statement travels with the appeal for the
    # review queue; internal notes are never serialized for the appellant.
    out["statement"] = appeal.statement
    if include_internal:
        out["review_note"] = appeal.review_note
    return out
