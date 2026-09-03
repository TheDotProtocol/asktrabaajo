"""/api/v1/documents — controlled, audited document access.

Owners manage their documents and grants. Non-owners may read only when a
live grant exists (to them or their organization); every denied or granted
access is audited. A company never receives documents automatically.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.documents import DocumentAccessGrant, PersonDocument
from app.models.identity import User
from app.models.tenancy import Organization
from app.schemas.common import MessageResponse
from app.schemas.documents import (
    DocumentCreate,
    DocumentOut,
    DocumentWithGrants,
    GrantCreate,
    GrantOut,
)
from app.services import audit as audit_service
from app.services import document_access
from app.services.auth_service import get_person_for_user

router = APIRouter(prefix="/documents", tags=["documents"])


def _own_person(db: Session, user: User):
    person = get_person_for_user(db, user.id)
    if person is None:
        raise NotFoundError("Person profile not found for this account.")
    return person


def _own_document(db: Session, user: User, document_id: uuid.UUID) -> PersonDocument:
    person = _own_person(db, user)
    doc = db.get(PersonDocument, document_id)
    if doc is None or doc.is_archived or doc.person_id != person.id:
        raise NotFoundError("Document not found.")
    return doc


@router.post("", response_model=DocumentOut, status_code=201)
def create_document(
    body: DocumentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonDocument:
    person = _own_person(db, user)
    doc = document_access.create_document(
        db,
        person_id=person.id,
        name=body.name,
        doc_type=body.doc_type,
        storage_key=body.storage_key,
        mime_type=body.mime_type,
        size_bytes=body.size_bytes,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="document.created",
        resource_type="document",
        resource_id=doc.id,
    )
    db.commit()
    return doc


@router.get("", response_model=list[DocumentOut])
def list_my_documents(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list:
    person = _own_person(db, user)
    rows = db.scalars(
        select(PersonDocument)
        .where(PersonDocument.person_id == person.id)
        .where(PersonDocument.is_archived.is_(False))
        .order_by(PersonDocument.created_at.desc())
    ).all()
    return [DocumentOut.model_validate(r) for r in rows]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonDocument:
    doc, is_owner = document_access.resolve_document_for_user(
        db, document_id=document_id, user_id=user.id, actor_id=user.id
    )
    if not is_owner:
        audit_service.record(
            db,
            actor_id=user.id,
            action="document.access",
            resource_type="document",
            resource_id=doc.id,
        )
        db.commit()
    return doc


@router.delete("/{document_id}", response_model=MessageResponse)
def archive_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    doc = _own_document(db, user, document_id)
    doc.is_archived = True
    db.commit()
    audit_service.record(
        db,
        actor_id=user.id,
        action="document.archived",
        resource_type="document",
        resource_id=doc.id,
    )
    db.commit()
    return MessageResponse(message="Document archived.")


@router.get("/{document_id}/grants", response_model=list[GrantOut])
def list_grants(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    _own_document(db, user, document_id)
    rows = db.scalars(
        select(DocumentAccessGrant)
        .where(DocumentAccessGrant.document_id == document_id)
        .order_by(DocumentAccessGrant.granted_at.desc())
    ).all()
    return [GrantOut.model_validate(r) for r in rows]


@router.post("/{document_id}/grants", response_model=GrantOut, status_code=201)
def create_grant(
    document_id: uuid.UUID,
    body: GrantCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentAccessGrant:
    doc = _own_document(db, user, document_id)
    if body.grantee_user_id is not None:
        if db.get(User, body.grantee_user_id) is None:
            raise NotFoundError("Grantee user not found.")
    if body.grantee_organization_id is not None:
        if db.get(Organization, body.grantee_organization_id) is None:
            raise NotFoundError("Grantee organization not found.")
    grant = document_access.grant_document_access(
        db,
        document=doc,
        grantee_user_id=body.grantee_user_id,
        grantee_organization_id=body.grantee_organization_id,
        actor_id=user.id,
        purpose=body.purpose,
        expires_at=body.expires_at,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="document.granted",
        resource_type="document",
        resource_id=doc.id,
        metadata={
            "grant_id": str(grant.id),
            "grantee_user_id": str(body.grantee_user_id) if body.grantee_user_id else None,
            "grantee_organization_id": (
                str(body.grantee_organization_id)
                if body.grantee_organization_id
                else None
            ),
        },
    )
    db.commit()
    return grant


@router.delete("/{document_id}/grants/{grant_id}", response_model=MessageResponse)
def revoke_grant(
    document_id: uuid.UUID,
    grant_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _own_document(db, user, document_id)
    grant = db.get(DocumentAccessGrant, grant_id)
    if grant is None or grant.document_id != document_id:
        raise NotFoundError("Grant not found.")
    document_access.revoke_grant(db, grant=grant, actor_id=user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="document.grant.revoked",
        resource_type="document",
        resource_id=document_id,
        metadata={"grant_id": str(grant.id)},
    )
    db.commit()
    return MessageResponse(message="Grant revoked.")
