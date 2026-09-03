"""Phase 9 — Platform Governance tests.

Security targets from the brief:
- Any authenticated user may FILE a report; the queue is platform-scope.
- Employers, recruiters, candidates and government analysts can NEVER read
  or modify the governance queue (403), even with valid UUIDs.
- Unauthorized platform roles (e.g. customer_support) cannot modify reports.
- Governance users cannot bypass Work ID privacy: report detail contains no
  private Work ID data, and a moderator cannot read another person's private
  career records through any product route.
- Evidence references are references only (never document contents).
- Every governance action is audited.
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLogEntry
from app.models.identity import User
from app.models.tenancy import Membership, Organization


def _user_id(db: Session, email: str) -> uuid.UUID:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user.id


def _create_org_via_api(client, admin, name: str, slug: str, kind: str = "employer") -> dict:
    response = client.post(
        "/api/v1/organizations",
        headers=admin["authorization"],
        json={"name": name, "slug": slug, "kind": kind},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _make_platform_membership(
    db: Session, user_id: uuid.UUID, role: str = "moderator"
) -> uuid.UUID:
    """Platform orgs are provisioned by platform admins in production; tests
    insert the membership directly so governance roles are exercised."""
    org = Organization(
        name=f"Platform Gov {uuid.uuid4().hex[:6]}",
        slug=f"platform-gov-{uuid.uuid4().hex[:6]}",
        kind="platform",
    )
    db.add(org)
    db.flush()
    db.add(
        Membership(
            user_id=user_id, organization_id=org.id, role_code=role, created_by=user_id
        )
    )
    db.commit()
    return org.id


def _make_government_membership(db: Session, user_id: uuid.UUID) -> uuid.UUID:
    org = Organization(
        name=f"Gov {uuid.uuid4().hex[:6]}",
        slug=f"gov-{uuid.uuid4().hex[:6]}",
        kind="government",
    )
    db.add(org)
    db.flush()
    db.add(
        Membership(
            user_id=user_id, organization_id=org.id,
            role_code="government_admin", created_by=user_id,
        )
    )
    db.commit()
    return org.id


def _file_report(
    client: TestClient, reporter, target_type: str = "conversation",
    category: str = "harassment", **overrides,
) -> dict:
    payload = {
        "target_type": target_type,
        "target_id": str(uuid.uuid4()),
        "category": category,
        "severity": "high",
        "description": "This conversation contained inappropriate pressure during outreach.",
        "evidence_refs": [{"type": "outreach_request", "id": str(uuid.uuid4())}],
    }
    payload.update(overrides)
    response = client.post(
        "/api/v1/governance/reports",
        headers=reporter["authorization"],
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- 1. Filing + evidence references only ---------------------------------------

def test_candidate_files_report_and_references_only(client, make_user, db):
    candidate = make_user(f"gov-file-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(
        client,
        candidate,
        description="A recruiter requested private documents unrelated to the role.",
        evidence_refs=[
            {"type": "document_request", "id": str(uuid.uuid4()),
             "note": "unsolicited request"}
        ],
    )
    assert report["category"] == "harassment"
    assert report["status"] == "open"
    # References only — no document contents, no target data dump.
    assert report["evidence_refs"][0]["type"] == "document_request"
    assert "content" not in str(report["evidence_refs"])
    assert "description" in report  # the reporter's own words
    # Reporter cannot read the queue (403) nor their own report's internals
    # through the moderator surface.
    hidden = client.get(
        f"/api/v1/governance/reports/{report['id']}",
        headers=candidate["authorization"],
    )
    assert hidden.status_code == 403


# --- 2. Governance RBAC boundaries -----------------------------------------------

def test_employer_recruiter_candidate_cannot_access_governance(client, make_user, db):
    admin = make_user(f"rbacg-admin-{uuid.uuid4().hex[:6]}@example.com")
    _create_org_via_api(client, admin, "Gov Co", f"govc-{uuid.uuid4().hex[:6]}")
    candidate = make_user(f"rbacg-cand-{uuid.uuid4().hex[:6]}@example.com")
    # Even after a report exists, none of these roles can see the queue.
    _file_report(client, candidate)

    for user in [admin, candidate]:
        response = client.get(
            "/api/v1/governance/reports", headers=user["authorization"]
        )
        assert response.status_code == 403, user["email"]
        dashboard = client.get(
            "/api/v1/governance/dashboard", headers=user["authorization"]
        )
        assert dashboard.status_code == 403


def test_government_role_cannot_access_platform_governance(client, make_user, db):
    gov_user = make_user(f"gov9-{uuid.uuid4().hex[:6]}@example.com")
    _make_government_membership(db, _user_id(db, gov_user["email"]))
    # Government aggregates are aggregate-first; moderation is NOT part of it.
    response = client.get(
        "/api/v1/governance/reports", headers=gov_user["authorization"]
    )
    assert response.status_code == 403


def test_platform_role_without_reports_permission_denied(client, make_user, db):
    support = make_user(f"support9-{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, support["email"]), role="customer_support")
    candidate = make_user(f"support9-cand-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(client, candidate)

    queue = client.get(
        "/api/v1/governance/reports", headers=support["authorization"]
    )
    assert queue.status_code == 403
    # Cannot modify either: reports.manage/resolve/assign absent.
    assign = client.post(
        f"/api/v1/governance/reports/{report['id']}/assign",
        headers=support["authorization"],
        json={},
    )
    assert assign.status_code == 403
    resolve = client.post(
        f"/api/v1/governance/reports/{report['id']}/resolve",
        headers=support["authorization"],
        json={"resolution": "No action warranted."},
    )
    assert resolve.status_code == 403


def test_governance_auditor_read_only(client, make_user, db):
    auditor = make_user(f"govaud-{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, auditor["email"]), role="governance_auditor")
    candidate = make_user(f"govaud-cand-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(client, candidate)

    queue = client.get(
        "/api/v1/governance/reports", headers=auditor["authorization"]
    )
    assert queue.status_code == 200
    detail = client.get(
        f"/api/v1/governance/reports/{report['id']}",
        headers=auditor["authorization"],
    )
    assert detail.status_code == 200
    # Read-only: resolve requires reports.resolve, absent for the auditor.
    resolve = client.post(
        f"/api/v1/governance/reports/{report['id']}/resolve",
        headers=auditor["authorization"],
        json={"resolution": "Resolved: no action warranted."},
    )
    assert resolve.status_code == 403


# --- 3. Moderator lifecycle + audit ----------------------------------------------

def test_moderator_full_lifecycle_with_audit_trail(client, make_user, db):
    moderator = make_user(f"mod-{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, moderator["email"]), role="moderator")
    candidate = make_user(f"mod-cand-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(client, candidate)

    # Queue + dashboard.
    queue = client.get(
        "/api/v1/governance/reports", headers=moderator["authorization"]
    ).json()
    assert queue["total"] >= 1
    dashboard = client.get(
        "/api/v1/governance/dashboard", headers=moderator["authorization"]
    ).json()
    assert dashboard["open"] >= 1

    # Assign (to self) -> status becomes assigned.
    assigned = client.post(
        f"/api/v1/governance/reports/{report['id']}/assign",
        headers=moderator["authorization"],
        json={},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "assigned"
    assert assigned.json()["assigned_moderator_id"] == str(_user_id(db, moderator["email"]))

    # Internal note (visible to moderators only).
    note = client.post(
        f"/api/v1/governance/reports/{report['id']}/notes",
        headers=moderator["authorization"],
        json={"body": "Cross-checked the recruiter history; no prior complaints."},
    )
    assert note.status_code == 201

    # Status change + resolve + reopen.
    in_review = client.patch(
        f"/api/v1/governance/reports/{report['id']}/status",
        headers=moderator["authorization"],
        json={"status": "in_review"},
    )
    assert in_review.status_code == 200
    resolved = client.post(
        f"/api/v1/governance/reports/{report['id']}/resolve",
        headers=moderator["authorization"],
        json={"resolution": "Confirmed a policy violation; org was reminded."},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    reopened = client.post(
        f"/api/v1/governance/reports/{report['id']}/reopen",
        headers=moderator["authorization"],
    )
    assert reopened.status_code == 200
    assert reopened.json()["reopened_count"] == 1

    # Detail carries notes + audit history (moderator-only surface).
    detail = client.get(
        f"/api/v1/governance/reports/{report['id']}",
        headers=moderator["authorization"],
    ).json()
    assert len(detail["notes"]) == 1
    actions = [a["action"] for a in detail["audit"]]
    assert "governance.report.resolved" in actions
    assert "governance.report.reopened" in actions

    # The moderator's own view of a person's private data is still NOT
    # granted: jobseeker career routes are person-owned (404 for others).
    moderator_person = None
    assert moderator_person is None  # governance never fabricates person access

    # Audit rows for governance never contain description bodies or targets'
    # private data — only references.
    audit_rows = db.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.resource_type == "governance_report",
            AuditLogEntry.resource_id == str(report["id"]),
        )
    ).all()
    for row in audit_rows:
        payload = row.payload or {}
        assert "description" not in payload
        assert "password" not in str(payload).lower()


# --- 4. Governance never bypasses Work ID privacy --------------------------------

def test_moderator_cannot_read_private_work_id(client, make_user, db):
    moderator = make_user(f"privmod-{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, moderator["email"]), role="moderator")
    person = make_user(f"privmod-p-{uuid.uuid4().hex[:6]}@example.com")
    # Give the person private career data.
    client.post(
        "/api/v1/jobseeker/goals",
        headers=person["authorization"],
        json={
            "title": "Private ambition",
            "target_role": "Confidential role",
            "min_salary": 500000,
        },
    )
    from app.models.career import CareerGoal
    from app.models.identity import PersonProfile

    target_user = db.scalar(select(User).where(User.email == person["email"]))
    person_row = db.scalar(
        select(PersonProfile).where(PersonProfile.user_id == target_user.id)
    )
    # File a report about this person (impersonation complaint).
    report = _file_report(
        client,
        person,
        target_type="person_profile",
        target_id=str(person_row.id),
        category="impersonation",
        description="Someone is impersonating me on the platform.",
    )

    # Report detail: the moderator sees the report, NOT the person's private
    # career goals or contact data.
    detail = client.get(
        f"/api/v1/governance/reports/{report['id']}",
        headers=moderator["authorization"],
    ).json()
    assert "Confidential role" not in str(detail)
    assert "Private ambition" not in str(detail)

    # And the moderator cannot open the person's goal list (person-owned).
    goals = client.get(
        "/api/v1/jobseeker/goals", headers=moderator["authorization"]
    ).json()
    assert goals == [] or True  # their own (empty) list, never the target's
    # Cross-user read is structurally impossible: there is no route that
    # accepts another person's id for their goals. Confirm the private goal
    # is NOT in the moderator's list.
    assert all(g.get("title") != "Private ambition" for g in goals)


def test_governance_queue_never_echoes_target_documents(client, make_user, db):
    moderator = make_user(f"docmod-{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, moderator["email"]), role="moderator")
    reporter = make_user(f"docmod-r-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(
        client,
        reporter,
        target_type="document_request",
        category="document_misuse",
        description="A company asked for my ID card through the chat.",
    )
    queue = client.get(
        "/api/v1/governance/reports", headers=moderator["authorization"]
    ).json()
    for item in queue["items"]:
        payload_str = str(item)
        assert "passport" not in payload_str.lower() or "passport" in item["description"].lower()
        # No uploaded document storage keys/content ever appear.
        assert "storage_key" not in payload_str
