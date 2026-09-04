"""Career Advisor API — deterministic intelligence over the caller's OWN Work ID.

All routes resolve the caller's PersonProfile server-side; nothing here
accepts another person's id, and no employer/governance surface exists.
These endpoints feed the functional jobseeker UI; the conversational
Athena surface reaches the same services through registered tools.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.identity import User
from app.services import career_advisor as career

router = APIRouter(prefix="/career-advisor", tags=["career-advisor"])


def _person_id(db: Session, user: User):
    return career.person_for_user(db, user.id).id


@router.get("/digest")
def career_digest(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Structured professional digest (whitelist only — no sensitive fields)."""
    return career.profile_digest(db, _person_id(db, user))


@router.get("/gaps")
def career_gaps(
    opportunity_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Matched / partial / missing skills against one opportunity or the goal."""
    import uuid

    opp_uuid = uuid.UUID(opportunity_id) if opportunity_id else None
    return career.skill_gap_analysis(db, _person_id(db, user), opportunity_id=opp_uuid)


@router.get("/paths")
def career_paths(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Advisory career-path steps anchored to the caller's profile."""
    return career.career_paths(db, _person_id(db, user))


@router.get("/opportunities")
def career_opportunities(
    mode: str = Query(default="strong", pattern="^(strong|potential|transition|explore)$"),
    limit: int = Query(default=10, ge=1, le=25),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Explainable opportunity recommendations (strong/potential/transition/explore)."""
    return career.opportunity_recommendations(
        db, _person_id(db, user), mode=mode, limit=limit
    )


@router.get("/applications")
def career_applications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Deterministic read of the caller's own application history."""
    return career.application_analysis(db, _person_id(db, user))


@router.get("/action-plan")
def career_action_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Suggestion-only action plan derived from the caller's Work ID + goal."""
    return career.action_plan(db, _person_id(db, user))
