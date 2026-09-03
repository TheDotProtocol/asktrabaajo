"""Controlled document access.

A document is visible to its owner and to holders of a live grant (user or
organization). Non-owners without a live grant receive 404 (existence is
hidden) and the attempt is audited as denied.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidInputError, NotFoundError
from app.core.timeutil import to_utc_naive, utc_now_naive
from app.models.documents import DocumentAccessGrant, PersonDocument
from app.models.tenancy import Membership
from app.services import audit as audit_service
from app.services.auth_service import get_person_for_user


def create_document(
    db: Session,
    *,
    person_id: uuid.UUID,
    name: str,
    doc_type: str,
    storage_key: Optional[str] = None,
    mime_type: Optional[str] = None,
    size_bytes: Optional[int] = None,
) -> PersonDocument:
    doc = PersonDocument(
        person_id=person_id,
        name=name,
        doc_type=doc_type,
        storage_key=storage_key,
        mime_type=mime_type,
        size_bytes=size_bytes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def grant_document_access(
    db: Session,
    *,
    document: PersonDocument,
    grantee_user_id: Optional[uuid.UUID],
    grantee_organization_id: Optional[uuid.UUID],
    actor_id: uuid.UUID,
    purpose: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> DocumentAccessGrant:
    if (grantee_user_id is None) == (grantee_organization_id is None):
        raise InvalidInputError(
            "Provide exactly one of grantee_user_id or grantee_organization_id."
        )
    grant = DocumentAccessGrant(
        document_id=document.id,
        grantee_user_id=grantee_user_id,
        grantee_organization_id=grantee_organization_id,
        purpose=purpose,
        granted_by=actor_id,
        expires_at=to_utc_naive(expires_at) if expires_at is not None else None,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def revoke_grant(db: Session, *, grant: DocumentAccessGrant, actor_id: uuid.UUID) -> None:
    grant.revoked_at = utc_now_naive()
    grant.revoked_by = actor_id
    db.commit()


def _is_live(grant: DocumentAccessGrant) -> bool:
    if grant.revoked_at is not None:
        return False
    if grant.expires_at is not None:
        # ``grant.expires_at`` may be naive (SQLite) or aware (PostgreSQL).
        now = utc_now_naive()
        expires = to_utc_naive(grant.expires_at)
        if expires <= now:
            return False
    return True


def find_live_grant_for_user(
    db: Session, document_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[DocumentAccessGrant]:
    """A live grant to the user directly or to an organization they belong to."""
    org_ids = [
        row[0]
        for row in db.execute(
            select(Membership.organization_id).where(Membership.user_id == user_id)
        )
    ]
    stmt = (
        select(DocumentAccessGrant)
        .where(DocumentAccessGrant.document_id == document_id)
        .where(DocumentAccessGrant.revoked_at.is_(None))
        .where(
            (DocumentAccessGrant.grantee_user_id == user_id)
            | (
                (DocumentAccessGrant.grantee_organization_id.isnot(None))
                & (DocumentAccessGrant.grantee_organization_id.in_(org_ids))
            )
        )
    )
    for grant in db.scalars(stmt):
        if _is_live(grant):
            return grant
    return None


def resolve_document_for_user(
    db: Session, *, document_id: uuid.UUID, user_id: uuid.UUID, actor_id: uuid.UUID
) -> Tuple[PersonDocument, bool]:
    """Return (document, is_owner) or raise NotFoundError (after auditing)."""
    doc = db.get(PersonDocument, document_id)
    if doc is None or doc.is_archived:
        raise NotFoundError("Document not found.")

    person = get_person_for_user(db, user_id)
    if person is not None and doc.person_id == person.id:
        return doc, True

    grant = find_live_grant_for_user(db, document_id, user_id)
    if grant is None:
        audit_service.record_committed(
            db,
            actor_id=actor_id,
            action="document.access.denied",
            resource_type="document",
            resource_id=document_id,
            result="denied",
        )
        raise NotFoundError("Document not found.")
    return doc, False
