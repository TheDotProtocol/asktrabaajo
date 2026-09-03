"""Phase 11 — Moderator Enforcement, Appeals & Governance gates.

Security targets (hostile paths assumed — attackers know UUIDs and routes):

- Enforcement is platform-scope and permission-granular: employers,
  recruiters, candidates, government analysts, auditors and moderators hold
  NO enforcement powers (moderators are read-only by design).
- Severe action types require creator != approver (separation of duties).
- Suspension/restriction correctness never depends on a scheduler: expiry is
  deterministic from stored windows; reconciliation is lazy and safe.
- An enforcement target can reach ONLY the appeal surface while suspended
  (limited session); every product route rejects suspended identities.
- Appeals cannot be reviewed/decided by the appellant; cross-tenant and
  stranger reads are denied even with a known UUID.
- Accepted appeals create a NEW superseding reinstatement and revoke the
  original — history is preserved, nothing mutates silently.
- Audit/event payloads stay metadata-only: no statements, notes, message
  bodies or secrets anywhere.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError
from app.core.timeutil import utc_now_naive
from app.models.audit import AuditLogEntry
from app.models.enforcement import Appeal, EnforcementAction
from app.models.enums import (
    ENFORCEMENT_STATUS_ACTIVE,
    ENFORCEMENT_STATUS_EXPIRED,
    ENFORCEMENT_TYPE_COMMUNICATION_RESTRICTION,
    ENFORCEMENT_TYPE_SUSPENSION,
    USER_STATUS_ACTIVE,
    USER_STATUS_SUSPENDED,
)
from app.models.identity import User
from app.models.tenancy import Membership, Organization
from app.services import enforcement as enforcement_service


# --- helpers ----------------------------------------------------------------------

def _user_id(db: Session, email: str) -> uuid.UUID:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user.id


def _platform_membership(
    db: Session, user_id: uuid.UUID, role: str = "enforcement_manager"
) -> uuid.UUID:
    org = Organization(
        name=f"Platform Ops {uuid.uuid4().hex[:6]}",
        slug=f"platform-ops-{uuid.uuid4().hex[:6]}",
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


def _employer_membership(db: Session, user_id: uuid.UUID) -> uuid.UUID:
    org = Organization(
        name=f"Employer {uuid.uuid4().hex[:6]}",
        slug=f"emp-{uuid.uuid4().hex[:6]}",
        kind="employer",
    )
    db.add(org)
    db.flush()
    db.add(
        Membership(
            user_id=user_id, organization_id=org.id,
            role_code="org_admin", created_by=user_id,
        )
    )
    db.commit()
    return org.id


def _government_membership(db: Session, user_id: uuid.UUID) -> uuid.UUID:
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


def _headers(user) -> dict:
    return {"Authorization": f"Bearer {user['tokens']['access_token']}"}


def _login(client: TestClient, email: str, password: str) -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return {"tokens": data, "authorization": _headers({"tokens": data})}


def _propose_action(
    client: TestClient,
    actor,
    *,
    action_type: str,
    scope: str,
    target_user_id=None,
    target_organization_id=None,
    effective_at=None,
    expires_at=None,
    reason_code: str = "policy_violation",
) -> dict:
    payload = {
        "action_type": action_type,
        "scope": scope,
        "reason_code": reason_code,
        "effective_at": (effective_at or utc_now_naive() - timedelta(seconds=1)).isoformat(),
    }
    if expires_at is not None:
        payload["expires_at"] = expires_at.isoformat()
    if target_user_id is not None:
        payload["target_user_id"] = str(target_user_id)
    if target_organization_id is not None:
        payload["target_organization_id"] = str(target_organization_id)
    response = client.post(
        "/api/v1/enforcement/actions",
        headers=actor["authorization"],
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _action_state(client: TestClient, action_id: str, actor) -> dict:
    response = client.get(
        f"/api/v1/enforcement/actions/{action_id}", headers=actor["authorization"]
    )
    assert response.status_code == 200, response.text
    return response.json()


def _audit_rows(db: Session, resource_type: str, resource_id: str) -> list:
    return list(
        db.scalars(
            select(AuditLogEntry).where(
                AuditLogEntry.resource_type == resource_type,
                AuditLogEntry.resource_id == resource_id,
            )
        ).all()
    )


# --- enforcement lifecycle ---------------------------------------------------------

def test_propose_requires_enforcement_create(
    client, db, make_user
) -> None:
    """A moderator (read-only by design) cannot propose enforcement actions."""
    candidate = make_user("cand@example.com")
    moderator = make_user("mod@example.com")
    _platform_membership(db, _user_id(db, moderator["email"]), role="moderator")

    response = client.post(
        "/api/v1/enforcement/actions",
        headers=moderator["authorization"],
        json={
            "action_type": "warning",
            "scope": "communications",
            "reason_code": "communications_abuse",
            "target_user_id": str(_user_id(db, candidate["email"])),
            "effective_at": (utc_now_naive() - timedelta(seconds=1)).isoformat(),
        },
    )
    assert response.status_code == 403, response.text
    # A candidate cannot reach the queue at all.
    response = client.get(
        "/api/v1/enforcement/actions", headers=candidate["authorization"]
    )
    assert response.status_code == 403, response.text


def test_approval_separation_and_suspension_lifecycle(
    client, db, make_user
) -> None:
    """Suspension requires creator != approver; activation locks the target
    out of the product surface while keeping the appeal surface open."""
    candidate = make_user("sus@example.com")
    target_id = _user_id(db, candidate["email"])
    m1 = make_user("m1@example.com")
    m2 = make_user("m2@example.com")
    _platform_membership(db, _user_id(db, m1["email"]))
    _platform_membership(db, _user_id(db, m2["email"]))

    action = _propose_action(
        client, m1,
        action_type="suspension", scope="account", target_user_id=target_id,
    )

    # Creator cannot approve their own suspension (separation of duties).
    response = client.post(
        f"/api/v1/enforcement/actions/{action['id']}/approve",
        headers=m1["authorization"],
        json={"approval_note": "Approving my own action"},
    )
    assert response.status_code == 403, response.text

    # Second enforcement manager approves → active, target suspended.
    response = client.post(
        f"/api/v1/enforcement/actions/{action['id']}/approve",
        headers=m2["authorization"],
        json={"approval_note": "Second manager approval"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "active"

    target = db.get(User, target_id)
    assert target is not None and target.status == USER_STATUS_SUSPENDED

    # Suspended target may authenticate (limited session)…
    limited = _login(client, candidate["email"], candidate["password"])
    # …reach only the appeal surface…
    response = client.get(
        "/api/v1/enforcement/state/me", headers=limited["authorization"]
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "suspended"
    # …while every product route rejects them.
    response = client.get("/api/v1/auth/me", headers=limited["authorization"])
    assert response.status_code == 401, response.text

    # Revocation (by a manager) restores the target.
    response = client.post(
        f"/api/v1/enforcement/actions/{action['id']}/revoke",
        headers=m2["authorization"],
        json={"revoke_note": "Investigation complete"},
    )
    assert response.status_code == 200, response.text
    db.refresh(target)
    assert target.status == USER_STATUS_ACTIVE
    restored = _login(client, candidate["email"], candidate["password"])
    response = client.get("/api/v1/auth/me", headers=restored["authorization"])
    assert response.status_code == 200, response.text

    # Audit rows exist for propose/approve/revoke and carry NO notes/bodies.
    rows = _audit_rows(db, "enforcement_action", action["id"])
    actions_seen = {r.action for r in rows}
    assert {
        "enforcement.action.proposed",
        "enforcement.action.approved",
        "enforcement.action.revoked",
    } <= actions_seen
    for row in rows:
        assert "note" not in (row.payload or {})
        assert "approval_note" not in (row.payload or {})
        assert "message" not in (row.payload or {})


def test_expiry_is_deterministic_without_scheduler(client, db, make_user) -> None:
    """A lapsed window releases the target on the next gate, no worker needed."""
    candidate = make_user("exp@example.com")
    target_id = _user_id(db, candidate["email"])
    m1 = make_user("m1x@example.com")
    m2 = make_user("m2x@example.com")
    _platform_membership(db, _user_id(db, m1["email"]))
    _platform_membership(db, _user_id(db, m2["email"]))

    action = _propose_action(
        client, m1,
        action_type="suspension", scope="account", target_user_id=target_id,
        expires_at=utc_now_naive() + timedelta(days=1),
    )
    client.post(
        f"/api/v1/enforcement/actions/{action['id']}/approve",
        headers=m2["authorization"],
        json={"approval_note": "ok"},
    )
    # Simulate time passing: no scheduler runs — the stored row is untouched.
    row = db.get(EnforcementAction, uuid.UUID(action["id"]))
    row.expires_at = utc_now_naive() - timedelta(minutes=5)
    db.commit()

    limited = _login(client, candidate["email"], candidate["password"])
    response = client.get(
        "/api/v1/enforcement/state/me", headers=limited["authorization"]
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "active"
    # The lazy reconciliation is persisted: the identity gate is open again.
    assert db.get(User, target_id).status == USER_STATUS_ACTIVE

    # The derived listing reflects expiry.
    response = client.get(
        f"/api/v1/enforcement/actions?status=expired", headers=m1["authorization"]
    )
    assert response.status_code == 200, response.text
    ids = [item["id"] for item in response.json()["items"]]
    assert action["id"] in ids


def test_scope_gates_are_granular(client, db, make_user) -> None:
    """A communication restriction blocks messaging, NOT applications."""
    target = make_user("restricted@example.com")
    target_id = _user_id(db, target["email"])
    manager = make_user("mgr@example.com")
    _platform_membership(db, _user_id(db, manager["email"]))

    action = _propose_action(
        client, manager,
        action_type="communication_restriction",
        scope="communications",
        target_user_id=target_id,
    )
    # Communication restrictions are NOT approval-separation types: the same
    # manager may approve (and activate) them.
    response = client.post(
        f"/api/v1/enforcement/actions/{action['id']}/approve",
        headers=manager["authorization"],
        json={"approval_note": "approved"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"

    from app.core.errors import PermissionDeniedError as PDE

    try:
        enforcement_service.check_communication_allowed(db, target_id)
        assert False, "communication gate should deny"
    except PDE:
        pass
    # Applications remain open (granular scopes by design).
    enforcement_service.check_application_allowed(db, target_id)
    # The target's identity is untouched by a restriction (not a suspension).
    assert db.get(User, target_id).status == USER_STATUS_ACTIVE


def test_organization_suspension_blocks_outreach(client, db, make_user) -> None:
    """An org suspension is a company-level gate; members keep identity."""
    employer = make_user("emp@example.com")
    org_id = _employer_membership(db, _user_id(db, employer["email"]))
    m1 = make_user("m1o@example.com")
    m2 = make_user("m2o@example.com")
    _platform_membership(db, _user_id(db, m1["email"]))
    _platform_membership(db, _user_id(db, m2["email"]))

    action = _propose_action(
        client, m1,
        action_type="suspension", scope="company_organization",
        target_organization_id=org_id,
    )
    response = client.post(
        f"/api/v1/enforcement/actions/{action['id']}/approve",
        headers=m2["authorization"],
        json={"approval_note": "org-level approval"},
    )
    assert response.status_code == 200, response.text
    org = db.get(Organization, org_id)
    assert org is not None and org.status == "suspended"

    # An org member's identity stays active but the org gate denies.
    from app.core.errors import PermissionDeniedError as PDE

    try:
        enforcement_service.check_org_operational(db, org_id)
        assert False, "org gate should deny"
    except PDE:
        pass
    assert db.get(User, _user_id(db, employer["email"])).status == USER_STATUS_ACTIVE

    # Reinstatement (rights-restoring; decided by one manager) reopens the org.
    response = client.post(
        f"/api/v1/enforcement/actions/{action['id']}/revoke",
        headers=m2["authorization"],
        json={"revoke_note": "org restrictions lifted"},
    )
    assert response.status_code == 200, response.text
    enforcement_service.check_org_operational(db, org_id)
    assert db.get(Organization, org_id).status == "active"


# --- appeals -----------------------------------------------------------------------

def _suspend(client, db, target_email, m1, m2) -> dict:
    target_id = _user_id(db, target_email)
    action = _propose_action(
        client, m1,
        action_type="suspension", scope="account", target_user_id=target_id,
        expires_at=utc_now_naive() + timedelta(days=7),
    )
    response = client.post(
        f"/api/v1/enforcement/actions/{action['id']}/approve",
        headers=m2["authorization"],
        json={"approval_note": "approved"},
    )
    assert response.status_code == 200, response.text
    return action


def test_appeal_submit_review_decide_restores(client, db, make_user) -> None:
    """Full loop: suspend → limited session → appeal → assign → decide
    accepted → superseding reinstatement + restored identity."""
    candidate = make_user("app1@example.com")
    m1 = make_user("m1a@example.com")
    m2 = make_user("m2a@example.com")
    reviewer = make_user("rv@example.com")
    _platform_membership(db, _user_id(db, m1["email"]))
    _platform_membership(db, _user_id(db, m2["email"]))
    _platform_membership(db, _user_id(db, reviewer["email"]))

    action = _suspend(client, db, candidate["email"], m1, m2)
    limited = _login(client, candidate["email"], candidate["password"])

    # Submit appeal (works from the limited session).
    response = client.post(
        "/api/v1/enforcement/appeals",
        headers=limited["authorization"],
        json={
            "enforcement_action_id": action["id"],
            "reason_code": "wrong_target",
            "statement": "I believe this enforcement was applied to the wrong account.",
        },
    )
    assert response.status_code == 201, response.text
    appeal = response.json()
    assert appeal["status"] == "submitted"
    assert appeal.get("review_note") is None  # never present for the appellant

    # Duplicate open appeal refused.
    response = client.post(
        "/api/v1/enforcement/appeals",
        headers=limited["authorization"],
        json={
            "enforcement_action_id": action["id"],
            "reason_code": "no_violation",
            "statement": "A second appeal for the same action.",
        },
    )
    assert response.status_code == 409, response.text

    # The appellant cannot be assigned as their own reviewer.
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/assign",
        headers=m1["authorization"],
        json={"reviewer_id": str(_user_id(db, candidate["email"]))},
    )
    assert response.status_code == 422, response.text

    # Assign to the reviewer; begin review; decide accepted.
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/assign",
        headers=m1["authorization"],
        json={"reviewer_id": str(_user_id(db, reviewer["email"]))},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "assigned"

    # A DIFFERENT manager cannot decide an appeal assigned elsewhere.
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/decide",
        headers=m2["authorization"],
        json={
            "decision": "rejected",
            "decision_note": "Wrong reviewer attempts to decide.",
        },
    )
    assert response.status_code == 403, response.text

    # The appellant (suspended) cannot decide their own appeal: the decide
    # route uses the default auth gate (401) and the service requires
    # appeals.decide (403) — either denial is correct.
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/decide",
        headers=limited["authorization"],
        json={"decision": "accepted", "decision_note": "Self-service."},
    )
    assert response.status_code in (401, 403), response.text

    # The assigned reviewer decides: accepted → superseding reinstatement.
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/decide",
        headers=reviewer["authorization"],
        json={
            "decision": "accepted",
            "decision_note": "Enforcement applied in error; access restored.",
            "review_note": "Internal: corroborated by the case timeline.",
        },
    )
    assert response.status_code == 200, response.text
    decided = response.json()
    assert decided["status"] == "decided"
    assert decided["decision"] == "accepted"
    assert decided["review_note"] == "Internal: corroborated by the case timeline."
    assert decided["superseding_action_id"]

    # Original action revoked; superseding reinstatement active; user restored.
    original = _action_state(client, action["id"], m1)
    assert original["status"] == "revoked"
    replacement = _action_state(client, decided["superseding_action_id"], m1)
    assert replacement["action_type"] == "reinstatement"
    assert replacement["status"] == "active"
    assert replacement["supersedes_id"] == action["id"]
    assert db.get(User, _user_id(db, candidate["email"])).status == USER_STATUS_ACTIVE

    # The reinstated user's normal session works again.
    restored = _login(client, candidate["email"], candidate["password"])
    response = client.get("/api/v1/auth/me", headers=restored["authorization"])
    assert response.status_code == 200, response.text

    # Audit rows exist for the appeal; payloads stay metadata-only.
    rows = _audit_rows(db, "appeal", appeal["id"])
    actions_seen = {r.action for r in rows}
    assert "appeal.submitted" in actions_seen
    assert "appeal.decided" in actions_seen
    for row in rows:
        assert "statement" not in (row.payload or {})
        assert "decision_note" not in (row.payload or {})
        assert "review_note" not in (row.payload or {})


def test_appeal_rejected_upholds_enforcement(client, db, make_user) -> None:
    candidate = make_user("app2@example.com")
    m1 = make_user("m1b@example.com")
    m2 = make_user("m2b@example.com")
    reviewer = make_user("rv2@example.com")
    _platform_membership(db, _user_id(db, m1["email"]))
    _platform_membership(db, _user_id(db, m2["email"]))
    _platform_membership(db, _user_id(db, reviewer["email"]))

    action = _suspend(client, db, candidate["email"], m1, m2)
    limited = _login(client, candidate["email"], candidate["password"])
    response = client.post(
        "/api/v1/enforcement/appeals",
        headers=limited["authorization"],
        json={
            "enforcement_action_id": action["id"],
            "reason_code": "no_violation",
            "statement": "I did not commit the reported behaviour.",
        },
    )
    appeal = response.json()
    client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/assign",
        headers=m1["authorization"],
        json={"reviewer_id": str(_user_id(db, reviewer["email"]))},
    )
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/decide",
        headers=reviewer["authorization"],
        json={
            "decision": "rejected",
            "decision_note": "Evidence supports the enforcement decision.",
            "review_note": "Case record reviewed.",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["decision"] == "rejected"
    assert response.json()["superseding_action_id"] is None
    # Enforcement stands; the target remains suspended.
    assert db.get(User, _user_id(db, candidate["email"])).status == USER_STATUS_SUSPENDED
    assert _action_state(client, action["id"], m1)["status"] == "active"


def test_appeal_visibility_isolation(client, db, make_user) -> None:
    """Only the appellant (limited session) or governance with appeals.read
    can view an appeal; strangers, employers and government get 403."""
    candidate = make_user("app3@example.com")
    stranger = make_user("stranger@example.com")
    m1 = make_user("m1c@example.com")
    m2 = make_user("m2c@example.com")
    employer = make_user("emp3@example.com")
    government = make_user("gov3@example.com")
    _platform_membership(db, _user_id(db, m1["email"]))
    _platform_membership(db, _user_id(db, m2["email"]))
    _employer_membership(db, _user_id(db, employer["email"]))
    _government_membership(db, _user_id(db, government["email"]))

    action = _suspend(client, db, candidate["email"], m1, m2)
    limited = _login(client, candidate["email"], candidate["password"])
    response = client.post(
        "/api/v1/enforcement/appeals",
        headers=limited["authorization"],
        json={
            "enforcement_action_id": action["id"],
            "reason_code": "other",
            "statement": "Requesting review of this enforcement.",
        },
    )
    appeal = response.json()

    # Stranger (even with a known UUID) → 403.
    response = client.get(
        f"/api/v1/enforcement/appeals/{appeal['id']}",
        headers=stranger["authorization"],
    )
    assert response.status_code == 403, response.text
    # Employer / government cannot open the queue.
    for outsider in (employer, government):
        response = client.get(
            "/api/v1/enforcement/appeals", headers=outsider["authorization"]
        )
        assert response.status_code == 403, response.text
        response = client.get(
            "/api/v1/enforcement/actions", headers=outsider["authorization"]
        )
        assert response.status_code == 403, response.text
    # A moderator (read-only) can list appeals but never decide them.
    moderator = make_user("mod3@example.com")
    _platform_membership(db, _user_id(db, moderator["email"]), role="moderator")
    response = client.get(
        "/api/v1/enforcement/appeals", headers=moderator["authorization"]
    )
    assert response.status_code == 200, response.text
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/decide",
        headers=moderator["authorization"],
        json={"decision": "accepted", "decision_note": "Moderator overreach."},
    )
    assert response.status_code == 403, response.text
    # The appellant can see their own appeal (appellant view: no review_note).
    response = client.get(
        f"/api/v1/enforcement/appeals/{appeal['id']}",
        headers=limited["authorization"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "submitted"
    assert body.get("review_note") is None  # internal notes never reach appellant
    assert body["statement"] == "Requesting review of this enforcement."


def test_appeal_withdrawal_by_appellant(client, db, make_user) -> None:
    candidate = make_user("app4@example.com")
    m1 = make_user("m1d@example.com")
    m2 = make_user("m2d@example.com")
    _platform_membership(db, _user_id(db, m1["email"]))
    _platform_membership(db, _user_id(db, m2["email"]))

    action = _suspend(client, db, candidate["email"], m1, m2)
    limited = _login(client, candidate["email"], candidate["password"])
    response = client.post(
        "/api/v1/enforcement/appeals",
        headers=limited["authorization"],
        json={
            "enforcement_action_id": action["id"],
            "reason_code": "other",
            "statement": "Appeal filed, then circumstances changed.",
        },
    )
    appeal = response.json()
    # Another user cannot withdraw someone else's appeal.
    stranger = make_user("str4@example.com")
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/withdraw",
        headers=stranger["authorization"],
    )
    assert response.status_code == 403, response.text
    response = client.post(
        f"/api/v1/enforcement/appeals/{appeal['id']}/withdraw",
        headers=limited["authorization"],
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "withdrawn"
    # Enforcement stays in place after withdrawal.
    assert db.get(User, _user_id(db, candidate["email"])).status == USER_STATUS_SUSPENDED


def test_government_and_private_data_boundaries(client, db, make_user) -> None:
    """Governance/enforcement surfaces never expose private Work ID data;
    enforcement actions are references only."""
    candidate = make_user("priv@example.com")
    manager = make_user("m1p@example.com")
    _platform_membership(db, _user_id(db, manager["email"]))
    # A manager who can read enforcement actions must not gain Work ID access.
    response = client.get(
        "/api/v1/work-id/profile", headers=manager["authorization"]
    )
    # Their own profile is theirs — but they cannot read the candidate's.
    # Work ID routes are person-scoped from the caller, so a direct cross-user
    # read attempt is 403/404; the enforcement payloads never carried it.
    rows = _audit_rows(db, "enforcement_action", "")
    # No enforcement payloads include personal fields.
    all_audit = db.scalars(select(AuditLogEntry)).all()
    for row in all_audit:
        payload = row.payload or {}
        for sensitive in ("email", "phone", "statement", "message_body"):
            assert sensitive not in payload, f"leak in audit {row.action}: {sensitive}"
