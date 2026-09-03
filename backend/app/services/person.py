"""Person service — privacy/visibility + profile completion.

Profile completion is computed from actual structured data with explicit,
configurable weights so the criteria can evolve without API changes.
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError
from app.models.enums import (
    VISIBILITY_LEVELS,
    VISIBILITY_PRIVATE,
    VISIBILITY_SCOPES,
)
from app.models.identity import PersonProfile, User
from app.models.privacy import PersonVisibilitySetting
from app.models.work import Credential, Education, Employment, UserSkill, WorkExperience

# Completion weights — configurable product criteria.
# Identity/contact are small but mandatory-feeling; structured journey data
# carries the weight so completion reflects a real, useful Work ID.
COMPLETION_WEIGHTS = {
    "identity": 0.10,   # full name + headline present
    "contact": 0.05,    # city/country present
    "verified_email": 0.05,
    "education": 0.15,  # ≥1 record
    "experience": 0.25,  # ≥1 record
    "employment": 0.15,  # ≥1 current/historical record
    "skills": 0.15,     # ≥3 skills
    "credentials": 0.10,  # ≥1 credential
}
_COMPLETION_THRESHOLDS = {
    "skills": 3,
    "experience": 1,
    "education": 1,
    "employment": 1,
    "credentials": 1,
}


def default_visibility_map() -> Dict[str, str]:
    return {scope: VISIBILITY_PRIVATE for scope in sorted(VISIBILITY_SCOPES)}


def get_visibility_map(db: Session, person_id: uuid.UUID) -> Dict[str, str]:
    rows = db.scalars(
        select(PersonVisibilitySetting).where(
            PersonVisibilitySetting.person_id == person_id
        )
    ).all()
    result = default_visibility_map()
    for row in rows:
        if row.scope in result:
            result[row.scope] = row.visibility
    return result


def set_visibility_map(
    db: Session, person_id: uuid.UUID, updates: Dict[str, str]
) -> Dict[str, str]:
    unknown = set(updates) - VISIBILITY_SCOPES
    if unknown:
        raise InvalidInputError(
            f"Unknown visibility scopes: {sorted(unknown)}. "
            f"Allowed: {sorted(VISIBILITY_SCOPES)}."
        )
    for scope, visibility in updates.items():
        if visibility not in VISIBILITY_LEVELS:
            raise InvalidInputError(
                f"Invalid visibility '{visibility}' for scope '{scope}'. "
                f"Allowed: {sorted(VISIBILITY_LEVELS)}."
            )
        setting = db.scalar(
            select(PersonVisibilitySetting).where(
                PersonVisibilitySetting.person_id == person_id,
                PersonVisibilitySetting.scope == scope,
            )
        )
        if setting is None:
            db.add(
                PersonVisibilitySetting(
                    person_id=person_id, scope=scope, visibility=visibility
                )
            )
        else:
            setting.visibility = visibility
    db.commit()
    return get_visibility_map(db, person_id)


def _count(db: Session, model, person_id: uuid.UUID) -> int:
    return len(
        db.scalars(select(model.id).where(model.person_id == person_id)).all()
    )


def profile_completion(
    db: Session, person: PersonProfile, user: User
) -> Dict:
    """Completion derived from real structured data + configured weights."""
    education = _count(db, Education, person.id)
    experience = _count(db, WorkExperience, person.id)
    employment = _count(db, Employment, person.id)
    skill_rows = _count(db, UserSkill, person.id)
    credentials = _count(db, Credential, person.id)

    checks = {
        "identity": bool(person.headline and user.full_name),
        "contact": bool(person.city and person.country_code),
        "verified_email": user.email_verified_at is not None,
        "education": education >= _COMPLETION_THRESHOLDS["education"],
        "experience": experience >= _COMPLETION_THRESHOLDS["experience"],
        "employment": employment >= _COMPLETION_THRESHOLDS["employment"],
        "skills": skill_rows >= _COMPLETION_THRESHOLDS["skills"],
        "credentials": credentials >= _COMPLETION_THRESHOLDS["credentials"],
    }
    earned = sum(weight for key, weight in COMPLETION_WEIGHTS.items() if checks[key])
    percent = int(round(earned * 100))

    return {
        "percent": percent,
        "earned_weight": round(earned, 4),
        "total_weight": 1.0,
        "sections": {
            key: {
                "met": checks[key],
                "weight": COMPLETION_WEIGHTS[key],
                "threshold": _COMPLETION_THRESHOLDS.get(key),
                "count": {
                    "education": education,
                    "experience": experience,
                    "employment": employment,
                    "skills": skill_rows,
                    "credentials": credentials,
                }.get(key),
            }
            for key in COMPLETION_WEIGHTS
        },
        "missing": [key for key in COMPLETION_WEIGHTS if not checks[key]],
    }
