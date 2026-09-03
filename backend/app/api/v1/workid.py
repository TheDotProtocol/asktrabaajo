"""/api/v1/work-id — the person's own professional identity spine.

Every resource here is person-owned. Ownership is enforced on every read,
write, and delete: another user asking for a resource id they do not own
receives 404 (existence is hidden).
"""
from __future__ import annotations

import uuid
from typing import Optional, Type, TypeVar

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import InvalidInputError, NotFoundError
from app.db.session import get_db
from app.models.enums import EDUCATION_LEVELS
from app.models.identity import PersonProfile, User
from app.models.work import (
    Credential,
    Education,
    Employment,
    Skill,
    UserSkill,
    WorkExperience,
)
from app.schemas.common import MessageResponse
from app.schemas.privacy import (
    CompletionOut,
    PrivacySettingsOut,
    PrivacyUpdateRequest,
)
from app.schemas.work import (
    CredentialCreate,
    CredentialOut,
    CredentialUpdate,
    EducationCreate,
    EducationOut,
    EducationUpdate,
    EmploymentCreate,
    EmploymentOut,
    ExperienceCreate,
    ExperienceOut,
    ExperienceUpdate,
    ProfileOut,
    ProfilePatch,
    UserSkillAdd,
    UserSkillOut,
    WorkIdSummary,
    is_valid_employment_type,
)
from app.services import audit as audit_service
from app.services import person as person_service
from app.services.auth_service import get_person_for_user

router = APIRouter(prefix="/work-id", tags=["work-id"])

M = TypeVar("M")

# --- helpers -----------------------------------------------------------------


def _person(db: Session, user: User) -> PersonProfile:
    person = get_person_for_user(db, user.id)
    if person is None:
        raise NotFoundError("Person profile not found for this account.")
    return person


def _owned(db: Session, person_id: uuid.UUID, model: Type[M], obj_id: uuid.UUID) -> M:
    """Fetch an object only if it belongs to this person; else 404."""
    obj = db.get(model, obj_id)
    if obj is None or getattr(obj, "person_id") != person_id:
        raise NotFoundError("Resource not found.")
    return obj


def _apply_patch(obj, values: dict) -> None:
    for key, value in values.items():
        setattr(obj, key, value)


# --- profile -----------------------------------------------------------------


@router.get("", response_model=WorkIdSummary)
def get_work_id(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkIdSummary:
    person = _person(db, user)
    experiences = db.scalars(
        select(WorkExperience)
        .where(WorkExperience.person_id == person.id)
        .order_by(WorkExperience.start_date.desc())
    ).all()
    educations = db.scalars(
        select(Education)
        .where(Education.person_id == person.id)
        .order_by(Education.start_date.desc())
    ).all()
    employments = db.scalars(
        select(Employment)
        .where(Employment.person_id == person.id)
        .order_by(Employment.start_date.desc())
    ).all()
    credentials = db.scalars(
        select(Credential)
        .where(Credential.person_id == person.id)
        .order_by(Credential.created_at.desc())
    ).all()
    skills = _user_skills(db, person.id)
    return WorkIdSummary(
        person=ProfileOut.model_validate(person),
        experiences=[ExperienceOut.model_validate(e) for e in experiences],
        educations=[EducationOut.model_validate(e) for e in educations],
        skills=skills,
        credentials=[CredentialOut.model_validate(c) for c in credentials],
        employments=[EmploymentOut.model_validate(e) for e in employments],
    )


@router.put("/profile", response_model=ProfileOut)
def update_profile(
    body: ProfilePatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonProfile:
    person = _person(db, user)
    _apply_patch(person, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(person)
    audit_service.record(
        db,
        actor_id=user.id,
        action="workid.profile.updated",
        resource_type="person_profile",
        resource_id=person.id,
    )
    db.commit()
    return person


# --- work experiences --------------------------------------------------------


@router.get("/experiences", response_model=list[ExperienceOut])
def list_experiences(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    person = _person(db, user)
    rows = db.scalars(
        select(WorkExperience)
        .where(WorkExperience.person_id == person.id)
        .order_by(WorkExperience.start_date.desc())
    ).all()
    return [ExperienceOut.model_validate(r) for r in rows]


@router.post("/experiences", response_model=ExperienceOut, status_code=201)
def create_experience(
    body: ExperienceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkExperience:
    person = _person(db, user)
    obj = WorkExperience(person_id=person.id, **body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/experiences/{experience_id}", response_model=ExperienceOut)
def update_experience(
    experience_id: uuid.UUID,
    body: ExperienceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkExperience:
    person = _person(db, user)
    obj = _owned(db, person.id, WorkExperience, experience_id)
    _apply_patch(obj, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/experiences/{experience_id}", response_model=MessageResponse)
def delete_experience(
    experience_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    obj = _owned(db, person.id, WorkExperience, experience_id)
    db.delete(obj)
    db.commit()
    return MessageResponse(message="Experience deleted.")


# --- education ---------------------------------------------------------------


@router.get("/educations", response_model=list[EducationOut])
def list_educations(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    person = _person(db, user)
    rows = db.scalars(
        select(Education)
        .where(Education.person_id == person.id)
        .order_by(Education.start_date.desc())
    ).all()
    return [EducationOut.model_validate(r) for r in rows]


@router.post("/educations", response_model=EducationOut, status_code=201)
def create_education(
    body: EducationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Education:
    person = _person(db, user)
    if body.level is not None and body.level not in EDUCATION_LEVELS:
        raise InvalidInputError(
            f"level must be one of {sorted(EDUCATION_LEVELS)} when provided."
        )
    obj = Education(person_id=person.id, **body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/educations/{education_id}", response_model=EducationOut)
def update_education(
    education_id: uuid.UUID,
    body: EducationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Education:
    person = _person(db, user)
    obj = _owned(db, person.id, Education, education_id)
    _apply_patch(obj, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/educations/{education_id}", response_model=MessageResponse)
def delete_education(
    education_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    obj = _owned(db, person.id, Education, education_id)
    db.delete(obj)
    db.commit()
    return MessageResponse(message="Education deleted.")


# --- skills (public catalog + own) -------------------------------------------


def _user_skills(db: Session, person_id: uuid.UUID) -> list:
    rows = db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person_id)
        .order_by(Skill.name)
    ).all()
    return [
        UserSkillOut(
            id=us.id,
            skill_id=skill.id,
            name=skill.name,
            category=skill.category,
            level=us.level,
            years_experience=us.years_experience,
        )
        for us, skill in rows
    ]


@router.get("/skills", response_model=list[UserSkillOut])
def list_my_skills(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    person = _person(db, user)
    return _user_skills(db, person.id)


@router.put("/skills", response_model=UserSkillOut)
def add_skill(
    body: UserSkillAdd,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserSkillOut:
    person = _person(db, user)
    skill = db.scalar(
        select(Skill).where(func.lower(Skill.name) == body.skill_name.lower())
    )
    if skill is None:
        skill = Skill(name=body.skill_name.strip())
        db.add(skill)
        db.flush()

    existing = db.scalar(
        select(UserSkill).where(
            UserSkill.person_id == person.id, UserSkill.skill_id == skill.id
        )
    )
    if existing is None:
        existing = UserSkill(
            person_id=person.id,
            skill_id=skill.id,
            level=body.level,
            years_experience=body.years_experience,
        )
        db.add(existing)
    else:
        existing.level = body.level
        existing.years_experience = body.years_experience
    db.commit()
    db.refresh(existing)
    return UserSkillOut(
        id=existing.id,
        skill_id=skill.id,
        name=skill.name,
        category=skill.category,
        level=existing.level,
        years_experience=existing.years_experience,
    )


@router.delete("/skills/{skill_id}", response_model=MessageResponse)
def remove_skill(
    skill_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    obj = db.scalar(
        select(UserSkill).where(
            UserSkill.person_id == person.id, UserSkill.skill_id == skill_id
        )
    )
    if obj is None:
        raise NotFoundError("Skill not found.")
    db.delete(obj)
    db.commit()
    return MessageResponse(message="Skill removed.")


# --- credentials -------------------------------------------------------------


@router.get("/credentials", response_model=list[CredentialOut])
def list_credentials(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    person = _person(db, user)
    rows = db.scalars(
        select(Credential)
        .where(Credential.person_id == person.id)
        .order_by(Credential.created_at.desc())
    ).all()
    return [CredentialOut.model_validate(r) for r in rows]


@router.post("/credentials", response_model=CredentialOut, status_code=201)
def create_credential(
    body: CredentialCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Credential:
    person = _person(db, user)
    obj = Credential(person_id=person.id, **body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    audit_service.record(
        db,
        actor_id=user.id,
        action="credential.created",
        resource_type="credential",
        resource_id=obj.id,
    )
    db.commit()
    return obj


@router.patch("/credentials/{credential_id}", response_model=CredentialOut)
def update_credential(
    credential_id: uuid.UUID,
    body: CredentialUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Credential:
    person = _person(db, user)
    obj = _owned(db, person.id, Credential, credential_id)
    _apply_patch(obj, body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(obj)
    audit_service.record(
        db,
        actor_id=user.id,
        action="credential.updated",
        resource_type="credential",
        resource_id=obj.id,
    )
    db.commit()
    return obj


@router.delete("/credentials/{credential_id}", response_model=MessageResponse)
def delete_credential(
    credential_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    obj = _owned(db, person.id, Credential, credential_id)
    db.delete(obj)
    db.commit()
    audit_service.record(
        db,
        actor_id=user.id,
        action="credential.deleted",
        resource_type="credential",
        resource_id=obj.id,
    )
    db.commit()
    return MessageResponse(message="Credential deleted.")


# --- employments -------------------------------------------------------------


@router.get("/employments", response_model=list[EmploymentOut])
def list_employments(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    person = _person(db, user)
    rows = db.scalars(
        select(Employment)
        .where(Employment.person_id == person.id)
        .order_by(Employment.start_date.desc())
    ).all()
    return [EmploymentOut.model_validate(r) for r in rows]


@router.post("/employments", response_model=EmploymentOut, status_code=201)
def create_employment(
    body: EmploymentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Employment:
    person = _person(db, user)
    if not is_valid_employment_type(body.employment_type):
        raise InvalidInputError(
            f"employment_type must be one of the supported values."
        )
    obj = Employment(person_id=person.id, **body.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/employments/{employment_id}", response_model=MessageResponse)
def delete_employment(
    employment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    obj = _owned(db, person.id, Employment, employment_id)
    db.delete(obj)
    db.commit()
    return MessageResponse(message="Employment record deleted.")


# --- profile completion + privacy --------------------------------------------


@router.get("/completion", response_model=CompletionOut)
def get_completion(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    person = _person(db, user)
    result = person_service.profile_completion(db, person, user)
    return CompletionOut(
        percent=result["percent"],
        sections={
            key: {
                "met": section["met"],
                "weight": section["weight"],
                "threshold": section.get("threshold"),
                "count": section.get("count"),
            }
            for key, section in result["sections"].items()
        },
        missing=result["missing"],
    )


@router.get("/privacy", response_model=PrivacySettingsOut)
def get_privacy(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrivacySettingsOut:
    person = _person(db, user)
    return PrivacySettingsOut(settings=person_service.get_visibility_map(db, person.id))


@router.put("/privacy", response_model=PrivacySettingsOut)
def update_privacy(
    body: PrivacyUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PrivacySettingsOut:
    person = _person(db, user)
    settings = person_service.set_visibility_map(db, person.id, body.settings)
    audit_service.record(
        db,
        actor_id=user.id,
        action="privacy.updated",
        resource_type="person_profile",
        resource_id=person.id,
    )
    db.commit()
    return PrivacySettingsOut(settings=settings)
