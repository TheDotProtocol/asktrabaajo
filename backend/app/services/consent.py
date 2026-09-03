"""Consent service — one reusable, person-owned consent model.

Answers: WHO consented, TO WHOM (user/org), TO ACCESS WHAT (scope), FOR WHAT
PURPOSE, WHEN, UNTIL WHEN, and WAS IT REVOKED. Enforced by later workflows
(applications, document disclosure, Athena actions); never buried in route
handlers.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError, NotFoundError
from app.core.timeutil import to_utc_naive, utc_now_naive
from app.models.enums import CONSENT_SCOPES
from app.models.privacy import Consent


def _is_live(consent: Consent) -> bool:
    if consent.revoked_at is not None:
        return False
    if consent.expires_at is not None:
        if to_utc_naive(consent.expires_at) <= utc_now_naive():
            return False
    return True


def create_consent(
    db: Session,
    *,
    person_id: uuid.UUID,
    grantee_user_id: Optional[uuid.UUID],
    grantee_organization_id: Optional[uuid.UUID],
    resource_scope: str,
    actor_id: uuid.UUID,
    purpose: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> Consent:
    if resource_scope not in CONSENT_SCOPES:
        raise InvalidInputError(
            f"resource_scope must be one of {sorted(CONSENT_SCOPES)}."
        )
    if (grantee_user_id is None) == (grantee_organization_id is None):
        raise InvalidInputError(
            "Provide exactly one of grantee_user_id or grantee_organization_id."
        )
    consent = Consent(
        person_id=person_id,
        grantee_user_id=grantee_user_id,
        grantee_organization_id=grantee_organization_id,
        resource_scope=resource_scope,
        purpose=purpose,
        granted_by=actor_id,
        expires_at=to_utc_naive(expires_at) if expires_at is not None else None,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


def revoke_consent(
    db: Session, *, consent: Consent, actor_id: uuid.UUID
) -> Consent:
    if consent.revoked_at is not None:
        return consent
    consent.revoked_at = utc_now_naive()
    consent.revoked_by = actor_id
    db.commit()
    db.refresh(consent)
    return consent


def list_person_consents(
    db: Session, person_id: uuid.UUID
) -> Sequence[Consent]:
    return db.scalars(
        select(Consent)
        .where(Consent.person_id == person_id)
        .order_by(Consent.granted_at.desc())
    ).all()


def get_person_consent(db: Session, person_id: uuid.UUID, consent_id: uuid.UUID) -> Consent:
    consent = db.get(Consent, consent_id)
    if consent is None or consent.person_id != person_id:
        raise NotFoundError("Consent not found.")
    return consent


def find_live_consent(
    db: Session,
    *,
    person_id: uuid.UUID,
    resource_scope: str,
    grantee_user_id: Optional[uuid.UUID] = None,
    grantee_organization_ids: Optional[List[uuid.UUID]] = None,
) -> Optional[Consent]:
    """Active consent matching person+scope+grantee (user or org list)."""
    stmt = select(Consent).where(
        Consent.person_id == person_id,
        Consent.resource_scope == resource_scope,
        Consent.revoked_at.is_(None),
    )
    for consent in db.scalars(stmt):
        if not _is_live(consent):
            continue
        if grantee_user_id is not None and consent.grantee_user_id == grantee_user_id:
            return consent
        if (
            grantee_organization_ids
            and consent.grantee_organization_id is not None
            and consent.grantee_organization_id in grantee_organization_ids
        ):
            return consent
    return None
