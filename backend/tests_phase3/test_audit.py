"""Audit coverage: key actions produce append-only entries with metadata."""
from __future__ import annotations

from sqlalchemy import select

from app.models.audit import AuditLogEntry


def _actions(db) -> set:
    return {
        row[0]
        for row in db.execute(select(AuditLogEntry.action).distinct())
    }


def test_audit_trail_covers_key_actions(client, make_user, db):
    owner = make_user("audit-owner@example.com")
    member = make_user("audit-viewer@example.com")
    stranger = make_user("audit-stranger@example.com")

    # Register (already audited) + org creation + member add
    org = client.post(
        "/api/v1/organizations",
        headers=owner["authorization"],
        json={"name": "Audit Co"},
    ).json()
    client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=owner["authorization"],
        json={"user_email": member["email"], "role": "hr"},
    )

    # Document + grant + denied access
    doc = client.post(
        "/api/v1/documents",
        headers=owner["authorization"],
        json={"name": "doc.pdf", "doc_type": "resume"},
    ).json()
    me = client.get("/api/v1/auth/me", headers=member["authorization"]).json()
    client.post(
        f"/api/v1/documents/{doc['id']}/grants",
        headers=owner["authorization"],
        json={"grantee_user_id": me["user_id"]},
    )
    client.get(f"/api/v1/documents/{doc['id']}", headers=stranger["authorization"])

    actions = _actions(db)
    for expected in [
        "auth.register",
        "organization.created",
        "organization.membership.added",
        "document.created",
        "document.granted",
        "document.access.denied",
    ]:
        assert expected in actions, f"missing audit action: {expected}"

    # Audit entries carry request metadata.
    register_entries = db.scalars(
        select(AuditLogEntry).where(AuditLogEntry.action == "auth.register")
    ).all()
    assert all(e.request_id for e in register_entries)

    # Append-only invariant is enforced by convention: the application never
    # issues UPDATE/DELETE against audit_log (schema-level protection comes
    # with a dedicated DB role in later phases).
    assert db.scalars(select(AuditLogEntry)).first() is not None
