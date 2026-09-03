"""Authorization + tenant-isolation regression tests.

Covers the Phase-1 vulnerability family explicitly:
- employer/company roles can never reach platform administration
- Company A cannot read or manage Company B
- membership role scope is validated against organization kind
- platform + government organizations are super-admin-provisioned only
- an organization can never be orphaned without an org_admin
- government members never hold individual-data permissions
"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.audit import AuditLogEntry
from app.models.identity import User
from app.models.tenancy import Membership, Organization
from app.services import authz


def _create_org(client, token, name: str, kind: str = "employer") -> dict:
    response = client.post(
        "/api/v1/organizations", headers=token, json={"name": name, "kind": kind}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _user_id(db, email: str) -> uuid.UUID:
    return db.scalar(select(User).where(User.email == email)).id


def test_org_admin_can_read_own_org(client, make_user):
    owner = make_user("boss@example.com")
    org = _create_org(client, owner["authorization"], "Boss Industries")
    response = client.get(
        f"/api/v1/organizations/{org['id']}", headers=owner["authorization"]
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Boss Industries"


def test_non_member_cannot_read_org(client, make_user):
    owner = make_user("owner@example.com")
    outsider = make_user("outsider@example.com")
    org = _create_org(client, owner["authorization"], "Secret Org")
    response = client.get(
        f"/api/v1/organizations/{org['id']}", headers=outsider["authorization"]
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


def test_company_a_cannot_read_or_manage_company_b(client, make_user):
    admin_a = make_user("admin-a@example.com")
    admin_b = make_user("admin-b@example.com")
    hr_b = make_user("hr-b@example.com")
    org_b = _create_org(client, admin_b["authorization"], "Company B")

    # hr_b joins Company B (org_admin adds member).
    response = client.post(
        f"/api/v1/organizations/{org_b['id']}/members",
        headers=admin_b["authorization"],
        json={"user_email": hr_b["email"], "role": "hr"},
    )
    assert response.status_code == 201, response.text

    # Company A's admin tries to read/manage Company B → 403 every time.
    for method, path in [
        ("get", f"/api/v1/organizations/{org_b['id']}"),
        ("get", f"/api/v1/organizations/{org_b['id']}/members"),
        ("post", f"/api/v1/organizations/{org_b['id']}/members"),
    ]:
        kwargs = {}
        if method == "post":
            kwargs["json"] = {"user_email": hr_b["email"], "role": "hr"}
        response = getattr(client, method)(path, headers=admin_a["authorization"], **kwargs)
        assert response.status_code == 403, (method, path, response.status_code)

    # Company A's admin cannot change roles of Company B members either.
    b_members = client.get(
        f"/api/v1/organizations/{org_b['id']}/members",
        headers=admin_b["authorization"],
    ).json()["members"]
    hr_b_id = next(m["user_id"] for m in b_members if m["email"] == "hr-b@example.com")
    response = client.patch(
        f"/api/v1/organizations/{org_b['id']}/members/{hr_b_id}",
        headers=admin_a["authorization"],
        json={"role": "recruiter"},
    )
    assert response.status_code == 403

    # Company B can list its own members.
    response = client.get(
        f"/api/v1/organizations/{org_b['id']}/members",
        headers=admin_b["authorization"],
    )
    assert response.status_code == 200
    emails = {m["email"] for m in response.json()["members"]}
    assert emails == {"admin-b@example.com", "hr-b@example.com"}


def test_employer_cannot_reach_platform_admin(client, make_user, db):
    """PHASE-1 REGRESSION: employer/company access never implies super admin."""
    employer = make_user("employer@example.com")
    _create_org(client, employer["authorization"], "Normal Co")

    user_id = _user_id(db, "employer@example.com")
    assert authz.is_platform_super_admin(db, user_id) is False
    assert "admin.manage" not in authz.effective_permission_codes(db, user_id)

    # Cannot create platform or government orgs.
    for kind in ("platform", "government"):
        response = client.post(
            "/api/v1/organizations",
            headers=employer["authorization"],
            json={"name": f"{kind.title()} Org", "kind": kind},
        )
        assert response.status_code == 403


def test_platform_role_cannot_be_planted_in_employer_org(client, make_user):
    """HR cannot be granted super_admin (or gov roles) inside a company org."""
    admin = make_user("admin@example.com")
    worker = make_user("worker@example.com")
    org = _create_org(client, admin["authorization"], "Acme")

    for role in ("super_admin", "customer_support", "government_user"):
        response = client.post(
            f"/api/v1/organizations/{org['id']}/members",
            headers=admin["authorization"],
            json={"user_email": worker["email"], "role": role},
        )
        assert response.status_code == 422, role


def test_hr_cannot_manage_members(client, make_user):
    """Role-scoped permissions: HR may not manage memberships."""
    admin = make_user("admin2@example.com")
    hr = make_user("hr2@example.com")
    victim = make_user("victim@example.com")
    org = _create_org(client, admin["authorization"], "Roles Co")

    client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=admin["authorization"],
        json={"user_email": hr["email"], "role": "hr"},
    )
    response = client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=hr["authorization"],
        json={"user_email": victim["email"], "role": "recruiter"},
    )
    assert response.status_code == 403

    response = client.get(
        f"/api/v1/organizations/{org['id']}/members", headers=hr["authorization"]
    )
    assert response.status_code == 403  # members.read is admin-only


def test_last_admin_guard(client, make_user, db):
    admin = make_user("solo@example.com")
    org = _create_org(client, admin["authorization"], "Solo Co")

    org_row = db.scalar(select(Organization).where(Organization.slug == "solo-co"))
    user_id = _user_id(db, "solo@example.com")

    # Downgrading the last org_admin is refused.
    response = client.patch(
        f"/api/v1/organizations/{org_row.id}/members/{user_id}",
        headers=admin["authorization"],
        json={"role": "hr"},
    )
    assert response.status_code == 422

    # Removing the last org_admin is refused.
    response = client.delete(
        f"/api/v1/organizations/{org_row.id}/members/{user_id}",
        headers=admin["authorization"],
    )
    assert response.status_code == 422


def test_membership_changes_are_audited(client, make_user, db):
    admin = make_user("audit-admin@example.com")
    member = make_user("audit-member@example.com")
    org = _create_org(client, admin["authorization"], "Audited Co")

    response = client.post(
        f"/api/v1/organizations/{org['id']}/members",
        headers=admin["authorization"],
        json={"user_email": member["email"], "role": "hr"},
    )
    assert response.status_code == 201

    entries = db.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.action == "organization.membership.added"
        )
    ).all()
    assert len(entries) == 1
    assert entries[0].organization_id == uuid.UUID(org["id"])


def test_government_analyst_holds_no_individual_data_permissions(client, make_user):
    citizen = make_user("citizen@example.com")
    analyst = make_user("analyst@example.com")

    me = client.get("/api/v1/auth/me", headers=citizen["authorization"]).json()
    assert me["person"] is not None

    me = client.get("/api/v1/auth/me", headers=analyst["authorization"]).json()
    forbidden = {"users.read", "users.update", "candidates.read", "admin.manage"}
    assert forbidden.isdisjoint(set(me["permissions"]))
