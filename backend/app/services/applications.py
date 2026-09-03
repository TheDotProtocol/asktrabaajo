"""Application lifecycle — the controlled state machine.

Every status change goes through ``transition`` and is recorded as an
``ApplicationEvent``. The jobseeker may only perform the self-service actions
defined in ``APPLICATION_USER_ACTIONS`` (apply, withdraw). Employer-driven
transitions (received -> screening -> interview -> offer) will arrive through
the same function in later phases, behind membership permission checks —
never as raw status writes.

Guarantees:
- a person cannot apply twice to the same opportunity (unique constraint + check)
- withdrawing is only possible from live (non-terminal, non-offer) states
- every transition is audited on the application timeline
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError, NotFoundError
from app.core.timeutil import utc_now_naive
from app.models.career import ApplicationEvent, JobApplication, Opportunity
from app.models.enums import (
    APPLICATION_STATUS_APPLIED,
    APPLICATION_STATUS_DISCOVERED,
    APPLICATION_STATUS_SAVED,
    APPLICATION_STATUS_WITHDRAWN,
    APPLICATION_STATUS_USER_ACTIONS,
)
from app.models.work import UserSkill


def save_opportunity(db: Session, person_id: uuid.UUID, opportunity_id: uuid.UUID) -> JobApplication:
    """Jobseeker saves an opportunity (creates a `saved` application record)."""
    _ensure_opportunity(db, opportunity_id)
    existing = _find(db, person_id, opportunity_id)
    if existing is not None:
        if existing.status == APPLICATION_STATUS_DISCOVERED:
            existing.status = APPLICATION_STATUS_SAVED
            db.commit()
            db.refresh(existing)
        return existing
    app = JobApplication(
        person_id=person_id,
        opportunity_id=opportunity_id,
        status=APPLICATION_STATUS_SAVED,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return app


def _find(
    db: Session, person_id: uuid.UUID, opportunity_id: uuid.UUID
) -> Optional[JobApplication]:
    return db.scalar(
        select(JobApplication).where(
            JobApplication.person_id == person_id,
            JobApplication.opportunity_id == opportunity_id,
        )
    )


def _ensure_opportunity(db: Session, opportunity_id: uuid.UUID) -> Opportunity:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None or opp.status != "active":
        raise NotFoundError("Opportunity not found or no longer active.")
    return opp


def apply(
    db: Session,
    person_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    cover_note: Optional[str] = None,
) -> JobApplication:
    """Apply to an opportunity from a saved/discovered record."""
    _ensure_opportunity(db, opportunity_id)
    # Marketplace-integrity gate: applying requires a minimum real Work ID
    # footprint (jobseekers stay free, but spam from empty profiles hurts
    # every company on the platform).
    if not db.scalars(
        select(UserSkill.id).where(UserSkill.person_id == person_id).limit(1)
    ).first():
        raise InvalidInputError(
            "Add at least one skill to your Work ID before applying."
        )

    application = _find(db, person_id, opportunity_id)
    if application is None:
        application = JobApplication(
            person_id=person_id,
            opportunity_id=opportunity_id,
            status=APPLICATION_STATUS_SAVED,
        )
        db.add(application)
        db.flush()

    allowed_from = APPLICATION_STATUS_USER_ACTIONS["apply"]["from"]
    if application.status not in allowed_from:
        raise InvalidInputError(
            f"Cannot apply from status '{application.status}'."
        )
    return _transition(
        db,
        application,
        APPLICATION_STATUS_APPLIED,
        actor_user_id=actor_user_id,
        note="Application submitted.",
    )


def withdraw(
    db: Session,
    person_id: uuid.UUID,
    application_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: Optional[str] = None,
) -> JobApplication:
    """Jobseeker withdraws a live application."""
    application = db.get(JobApplication, application_id)
    if application is None or application.person_id != person_id:
        raise NotFoundError("Application not found.")

    allowed_from = APPLICATION_STATUS_USER_ACTIONS["withdraw"]["from"]
    if application.status not in allowed_from:
        raise InvalidInputError(
            f"Cannot withdraw from status '{application.status}'."
        )
    app = _transition(
        db,
        application,
        APPLICATION_STATUS_WITHDRAWN,
        actor_user_id=actor_user_id,
        note=reason or "Withdrawn by candidate.",
    )
    app.withdrawn_at = utc_now_naive()
    db.commit()
    db.refresh(app)
    return app


def _transition(
    db: Session,
    application: JobApplication,
    to_status: str,
    actor_user_id: uuid.UUID,
    note: Optional[str] = None,
) -> JobApplication:
    from_status = application.status
    if from_status == to_status:
        return application
    application.status = to_status
    application.last_activity_at = utc_now_naive()
    if to_status == APPLICATION_STATUS_APPLIED and application.applied_at is None:
        application.applied_at = utc_now_naive()
    db.add(
        ApplicationEvent(
            application_id=application.id,
            from_status=from_status,
            to_status=to_status,
            note=note,
            actor_user_id=actor_user_id,
        )
    )
    db.commit()
    db.refresh(application)
    return application


def transition_to_status(
    db: Session,
    application: JobApplication,
    to_status: str,
    actor_user_id: uuid.UUID,
    note: Optional[str] = None,
) -> JobApplication:
    """Programmatic transition used by trusted server-side flows.

    Public because server-side workflows (e.g. offer accepted -> application
    accepted) must move the application through the same audited state
    machine. Employer-driven transitions will pass through here in later
    phases behind membership permission checks. The jobseeker API itself
    never calls this with arbitrary statuses.
    """
    from app.models.enums import APPLICATION_STATUSES

    if to_status not in APPLICATION_STATUSES:
        raise InvalidInputError(f"Unknown application status '{to_status}'.")
    return _transition(
        db,
        application,
        to_status,
        actor_user_id=actor_user_id,
        note=note,
    )


def apply_to_matching(
    db: Session,
    person_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    opportunity_ids: list,
) -> dict:
    """Explicit batch action — ONLY ever runs on the caller's explicit list.

    This is the building block Athena will one day invoke after the user
    authorizes 'apply to all suitable opportunities'; the authorization,
    rate limiting, and per-company requirements live at that boundary.
    """
    applied, failed = [], []
    for opportunity_id in opportunity_ids:
        try:
            result = apply(
                db,
                person_id,
                uuid.UUID(str(opportunity_id)),
                actor_user_id=actor_user_id,
            )
            applied.append(str(result.id))
        except Exception as exc:  # per-item failure isolation
            failed.append({"opportunity_id": str(opportunity_id), "reason": str(exc)})
    return {"applied": applied, "failed": failed}
