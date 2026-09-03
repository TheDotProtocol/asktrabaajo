"""Controlled document access tests.

A company/recruiter never receives a jobseeker's documents automatically:
access requires an explicit, revocable, possibly expiring grant, and every
denied/authorized access is audited.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.audit import AuditLogEntry
from app.models.documents import DocumentAccessGrant

DOC = {"name": "cv.pdf", "doc_type": "resume", "mime_type": "application/pdf"}


def _make_doc(client, user) -> str:
    response = client.post(
        "/api/v1/documents", headers=user["authorization"], json=DOC
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_owner_can_create_list_fetch(client, make_user):
    user = make_user("doc-owner@example.com")
    doc_id = _make_doc(client, user)

    listed = client.get("/api/v1/documents", headers=user["authorization"])
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = client.get(f"/api/v1/documents/{doc_id}", headers=user["authorization"])
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "cv.pdf"


def test_non_owner_without_grant_gets_404_and_denial_is_audited(
    client, make_user, db
):
    """PHASE-3 REGRESSION: unauthorized users cannot download documents."""
    owner = make_user("owner@example.com")
    stranger = make_user("stranger@example.com")
    doc_id = _make_doc(client, owner)

    response = client.get(
        f"/api/v1/documents/{doc_id}", headers=stranger["authorization"]
    )
    assert response.status_code == 404  # existence hidden

    denied = db.scalars(
        select(AuditLogEntry).where(AuditLogEntry.action == "document.access.denied")
    ).all()
    assert len(denied) == 1
    assert denied[0].resource_id == doc_id
    assert denied[0].result == "denied"


def test_grant_to_user_enables_and_revokes_access(client, make_user, db):
    owner = make_user("owner2@example.com")
    recruiter = make_user("recruiter@example.com")
    doc_id = _make_doc(client, owner)

    # Grant access to the recruiter (fetch their user id via /auth/me).
    me = client.get("/api/v1/auth/me", headers=recruiter["authorization"]).json()
    grant = client.post(
        f"/api/v1/documents/{doc_id}/grants",
        headers=owner["authorization"],
        json={"grantee_user_id": me["user_id"], "purpose": "application review"},
    )
    assert grant.status_code == 201, grant.text
    grant_id = grant.json()["id"]

    # Recruiter can now read the document (audited).
    fetched = client.get(f"/api/v1/documents/{doc_id}", headers=recruiter["authorization"])
    assert fetched.status_code == 200
    accesses = db.scalars(
        select(AuditLogEntry).where(AuditLogEntry.action == "document.access")
    ).all()
    assert len(accesses) == 1

    # Revoke → recruiter loses access.
    revoked = client.delete(
        f"/api/v1/documents/{doc_id}/grants/{grant_id}",
        headers=owner["authorization"],
    )
    assert revoked.status_code == 200
    response = client.get(f"/api/v1/documents/{doc_id}", headers=recruiter["authorization"])
    assert response.status_code == 404

    stored = db.get(DocumentAccessGrant, uuid.UUID(grant_id))
    assert stored.revoked_at is not None
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "document.grant.revoked")
    )


def test_expired_grant_denies_access(client, make_user):
    owner = make_user("owner3@example.com")
    viewer = make_user("viewer@example.com")
    doc_id = _make_doc(client, owner)
    me = client.get("/api/v1/auth/me", headers=viewer["authorization"]).json()

    past = datetime.now(timezone.utc) - timedelta(minutes=5)
    grant = client.post(
        f"/api/v1/documents/{doc_id}/grants",
        headers=owner["authorization"],
        json={"grantee_user_id": me["user_id"], "expires_at": past.isoformat()},
    )
    assert grant.status_code == 201

    response = client.get(f"/api/v1/documents/{doc_id}", headers=viewer["authorization"])
    assert response.status_code == 404


def test_grant_to_organization_enables_all_members(client, make_user):
    owner = make_user("owner4@example.com")
    admin = make_user("admin4@example.com")
    member = make_user("member4@example.com")
    outsider = make_user("outsider4@example.com")
    doc_id = _make_doc(client, owner)

    org = client.post(
        "/api/v1/organizations",
        headers=admin["authorization"],
        json={"name": "Recruiter Co", "kind": "employer"},
    ).json()
    client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=admin["authorization"],
        json={"user_email": member["email"], "role": "hr"},
    )

    grant = client.post(
        f"/api/v1/documents/{doc_id}/grants",
        headers=owner["authorization"],
        json={"grantee_organization_id": org["id"]},
    )
    assert grant.status_code == 201

    # Any member of the org can read; outsiders still cannot.
    assert (
        client.get(f"/api/v1/documents/{doc_id}", headers=member["authorization"]).status_code
        == 200
    )
    assert (
        client.get(f"/api/v1/documents/{doc_id}", headers=outsider["authorization"]).status_code
        == 404
    )


def test_only_owner_can_grant_or_archive(client, make_user):
    owner = make_user("owner5@example.com")
    other = make_user("other5@example.com")
    doc_id = _make_doc(client, owner)

    grant = client.post(
        f"/api/v1/documents/{doc_id}/grants",
        headers=other["authorization"],
        json={"grantee_user_id": "00000000-0000-0000-0000-000000000000"},
    )
    # other is not the owner → 404 (hidden) even before grantee validation.
    assert grant.status_code == 404

    archived = client.delete(f"/api/v1/documents/{doc_id}", headers=other["authorization"])
    assert archived.status_code == 404


def test_grant_requires_exactly_one_grantee(client, make_user):
    owner = make_user("owner6@example.com")
    doc_id = _make_doc(client, owner)
    response = client.post(
        f"/api/v1/documents/{doc_id}/grants",
        headers=owner["authorization"],
        json={},
    )
    assert response.status_code == 422
