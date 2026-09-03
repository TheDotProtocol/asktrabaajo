"""Phase 4 — privacy boundaries + consent ownership tests.

A person's consent and visibility settings belong to the person:
- user A can never read/change/revoke user B's consents or visibility
- contact details stay out of ordinary APIs
- company membership never grants access to a person's private Work ID
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.audit import AuditLogEntry
from app.models.identity import User

PASSWORD = "StrongPass123!"
PRIVATE_SCOPES = [
    "profile", "contact", "education", "experience", "employment",
    "skills", "credentials", "documents",
]


def _user_id(db, email):
    return db.scalar(select(User).where(User.email == email)).id


def test_privacy_defaults_are_private(client, make_user):
    user = make_user("privacy@example.com", password=PASSWORD)
    r = client.get("/api/v1/work-id/privacy", headers=user["authorization"])
    assert r.status_code == 200
    settings = r.json()["settings"]
    assert set(settings) == set(PRIVATE_SCOPES)
    assert all(v == "private" for v in settings.values())


def test_privacy_update_and_validation(client, make_user):
    user = make_user("privacy2@example.com", password=PASSWORD)
    headers = user["authorization"]

    r = client.put(
        "/api/v1/work-id/privacy",
        headers=headers,
        json={"settings": {"skills": "public", "profile": "public"}},
    )
    assert r.status_code == 200
    assert r.json()["settings"]["skills"] == "public"
    assert r.json()["settings"]["contact"] == "private"  # untouched stays private

    # Invalid scope or value → 422.
    assert (
        client.put(
            "/api/v1/work-id/privacy",
            headers=headers,
            json={"settings": {"bank_balance": "public"}},
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/v1/work-id/privacy",
            headers=headers,
            json={"settings": {"skills": "everyone"}},
        ).status_code
        == 422
    )


def test_contact_details_not_exposed_via_me(client, make_user):
    user = make_user("contact@example.com", password=PASSWORD)
    headers = user["authorization"]
    client.put(
        "/api/v1/work-id/profile",
        headers=headers,
        json={"headline": "Engineer", "phone": "+971500000000", "city": "Dubai"},
    )
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["person"]["headline"] == "Engineer"
    # Contact/private fields never appear on the public me summary.
    assert "phone" not in me["person"]
    assert "date_of_birth" not in me["person"]


def test_user_b_cannot_touch_user_a_consents(client, make_user, db):
    alice = make_user("alice-c@example.com", password=PASSWORD)
    bob = make_user("bob-c@example.com", password=PASSWORD)

    grant = client.post(
        "/api/v1/work-id/consents",
        headers=alice["authorization"],
        json={
            "grantee_user_id": str(_user_id(db, "bob-c@example.com")),
            "resource_scope": "work_id:documents",
            "purpose": "recruitment review",
        },
    )
    assert grant.status_code == 201, grant.text
    consent_id = grant.json()["id"]
    assert grant.json()["active"] is True

    # Bob cannot revoke Alice's consent — 404 (existence hidden).
    r = client.delete(
        f"/api/v1/work-id/consents/{consent_id}", headers=bob["authorization"]
    )
    assert r.status_code == 404

    # Bob's own consent list does not contain Alice's consent.
    mine = client.get("/api/v1/work-id/consents", headers=bob["authorization"]).json()
    assert mine == []
    assert grant.json()["resource_scope"] == "work_id:documents"

    # Alice revokes her own consent.
    revoked = client.delete(
        f"/api/v1/work-id/consents/{consent_id}", headers=alice["authorization"]
    )
    assert revoked.status_code == 200
    listed = client.get("/api/v1/work-id/consents", headers=alice["authorization"]).json()
    assert listed[0]["active"] is False
    assert listed[0]["revoked_at"] is not None
    assert db.scalar(
        select(AuditLogEntry).where(AuditLogEntry.action == "consent.revoked")
    )


def test_consent_to_organization_and_validation(client, make_user):
    owner = make_user("consent-org@example.com", password=PASSWORD)
    org_admin = make_user("consent-orgadmin@example.com", password=PASSWORD)
    org = client.post(
        "/api/v1/organizations",
        headers=org_admin["authorization"],
        json={"name": "Consent Co", "kind": "employer"},
    ).json()

    grant = client.post(
        "/api/v1/work-id/consents",
        headers=owner["authorization"],
        json={
            "grantee_organization_id": org["id"],
            "resource_scope": "work_id:credentials",
        },
    )
    assert grant.status_code == 201
    assert grant.json()["grantee_organization_id"] == org["id"]

    # Both grantee fields at once → 422; unknown scope → 422.
    bad = client.post(
        "/api/v1/work-id/consents",
        headers=owner["authorization"],
        json={
            "grantee_user_id": "00000000-0000-0000-0000-000000000000",
            "grantee_organization_id": org["id"],
            "resource_scope": "work_id:credentials",
        },
    )
    assert bad.status_code == 422
    bad = client.post(
        "/api/v1/work-id/consents",
        headers=owner["authorization"],
        json={
            "grantee_organization_id": org["id"],
            "resource_scope": "nonsense:scope",
        },
    )
    assert bad.status_code == 422


def test_company_membership_does_not_open_private_work_id(client, make_user):
    """A company interacting with people never owns their Work ID."""
    admin = make_user("co-admin@example.com", password=PASSWORD)
    person = make_user("person@example.com", password=PASSWORD)
    org = client.post(
        "/api/v1/organizations",
        headers=admin["authorization"],
        json={"name": "Big Co", "kind": "employer"},
    ).json()

    # HR-role member of Big Co still cannot see the person's Work ID.
    hr = make_user("co-hr@example.com", password=PASSWORD)
    client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=admin["authorization"],
        json={"user_email": hr["email"], "role": "hr"},
    )

    # The person's Work ID record belongs to the person: the company member's
    # /work-id is their own (empty), and they cannot mutate the person's
    # records — existence is hidden (404).
    created = client.post(
        "/api/v1/work-id/experiences",
        headers=person["authorization"],
        json={
            "company_name": "Acme",
            "title": "Engineer",
            "start_date": "2023-01-01",
            "is_current": True,
        },
    )
    assert created.status_code == 201
    exp_id = created.json()["id"]

    hr_workid = client.get("/api/v1/work-id", headers=hr["authorization"])
    assert hr_workid.status_code == 200
    assert hr_workid.json()["experiences"] == []  # HR sees only their own

    tamper = client.patch(
        f"/api/v1/work-id/experiences/{exp_id}",
        headers=hr["authorization"],
        json={"title": "Hijacked"},
    )
    assert tamper.status_code == 404

    # Company context works for company data, not personal identity.
    org_read = client.get(
        f"/api/v1/organizations/{org['id']}", headers=hr["authorization"]
    )
    assert org_read.status_code == 200
    assert org_read.json()["name"] == "Big Co"
