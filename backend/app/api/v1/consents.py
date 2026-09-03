"""/api/v1/work-id/consents — person-owned consent records.

Only the person (owner) can create, view, or revoke their consents. A
revocation by anyone else returns 404 (existence hidden) and is audited.
Consent never lives inside random route handlers — logic is in the reusable
``app.services.consent`` module.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.identity import User
from app.models.tenancy import Organization
from app.schemas.common import MessageResponse
from app.schemas.consent import ConsentCreate, ConsentOut
from app.services import audit as audit_service
from app.services import consent as consent_service
from app.models.identity import PersonProfile
from app.services.auth_service import get_person_for_user

router = APIRouter(prefix="/consents", tags=["consents"])


def _person(db: Session, user: User) -> PersonProfile:
    person = get_person_for_user(db, user.id)
    if person is None:
        raise NotFoundError("Person profile not found for this account.")
    return person


def _out(consent) -> ConsentOut:
    return ConsentOut(
        id=consent.id,
        person_id=consent.person_id,
        grantee_user_id=consent.grantee_user_id,
        grantee_organization_id=consent.grantee_organization_id,
        resource_scope=consent.resource_scope,
        purpose=consent.purpose,
        granted_at=consent.granted_at,
        expires_at=consent.expires_at,
        revoked_at=consent.revoked_at,
        active=consent.revoked_at is None,
    )


@router.get("", response_model=list)
def list_consents(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    person = _person(db, user)
    return [
        _out(consent).model_dump(mode="json")
        for consent in consent_service.list_person_consents(db, person.id)
    ]


@router.post("", response_model=ConsentOut, status_code=201)
def grant_consent(
    body: ConsentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentOut:
    person = _person(db, user)
    if body.grantee_user_id is not None and db.get(User, body.grantee_user_id) is None:
        raise NotFoundError("Grantee user not found.")
    if (
        body.grantee_organization_id is not None
        and db.get(Organization, body.grantee_organization_id) is None
    ):
        raise NotFoundError("Grantee organization not found.")
    consent = consent_service.create_consent(
        db,
        person_id=person.id,
        grantee_user_id=body.grantee_user_id,
        grantee_organization_id=body.grantee_organization_id,
        resource_scope=body.resource_scope,
        actor_id=user.id,
        purpose=body.purpose,
        expires_at=body.expires_at,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="consent.granted",
        resource_type="consent",
        resource_id=consent.id,
        metadata={
            "grantee_user_id": str(body.grantee_user_id) if body.grantee_user_id else None,
            "grantee_organization_id": (
                str(body.grantee_organization_id)
                if body.grantee_organization_id
                else None
            ),
            "resource_scope": body.resource_scope,
        },
    )
    db.commit()
    return _out(consent)


@router.delete("/{consent_id}", response_model=MessageResponse)
def revoke_consent(
    consent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    person = _person(db, user)
    consent = consent_service.get_person_consent(db, person.id, consent_id)
    consent_service.revoke_consent(db, consent=consent, actor_id=user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="consent.revoked",
        resource_type="consent",
        resource_id=consent.id,
    )
    db.commit()
    return MessageResponse(message="Consent revoked.")
