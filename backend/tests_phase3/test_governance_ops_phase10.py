"""Phase 10 — Governance Operations & Platform Control Room tests.

Security targets (hostile paths assumed — attackers know UUIDs and routes):

- Employers, recruiters, candidates, government analysts can never reach any
  governance surface (queue, teams, audit review, signals, moderators).
- Unauthorized platform roles cannot assign/escalate/resolve/change priority.
- Case assignment is team-aware; team boundaries hold.
- SLA state is deterministic and testable (no scheduler — lazy evaluation).
- Escalation, reopening, priority change and linking are audited; audit and
  event payloads stay reference-only (never descriptions, reasons, message
  bodies or secrets).
- Cross-tenant report linking is refused; case detail never exposes private
  Work ID data.
- Integrity signals are neutral ("review required"), never accusations.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utc_now_naive
from app.models.audit import AuditLogEntry
from app.models.career import UserNotification
from app.models.enums import (
    REPORT_SLA_HOURS,
    REPORT_PRIORITY_CRITICAL,
    SLA_STATE_BREACHED,
    SLA_STATE_DUE_SOON,
    SLA_STATE_ON_TRACK,
)
from app.models.governance import (
    GovernanceCaseLink,
    GovernanceReport,
    GovernanceTeam,
    GovernanceTeamMember,
)
from app.models.identity import User, PersonProfile
from app.models.platform import PlatformEvent
from app.models.tenancy import Membership, Organization
from app.services.governance import sla_state_for


# --- helpers ----------------------------------------------------------------------

def _user_id(db: Session, email: str) -> uuid.UUID:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user.id


def _make_platform_membership(
    db: Session, user_id: uuid.UUID, role: str = "moderator"
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


def _make_employer_membership(db: Session, user_id: uuid.UUID) -> uuid.UUID:
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
    client: TestClient,
    reporter,
    organization_id: str | None = None,
    category: str = "harassment",
    **overrides,
) -> dict:
    payload = {
        "target_type": "conversation",
        "target_id": str(uuid.uuid4()),
        "category": category,
        "severity": "high",
        "description": "Reported behaviour during outreach requires platform review.",
        "evidence_refs": [{"type": "outreach_request", "id": str(uuid.uuid4())}],
    }
    if organization_id:
        payload["organization_id"] = organization_id
    payload.update(overrides)
    response = client.post(
        "/api/v1/governance/reports",
        headers=reporter["authorization"],
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _moderator(client: TestClient, make_user, db, role: str = "moderator") -> dict:
    user = make_user(f"p10mod-{uuid.uuid4().hex[:6]}@example.com")
    _make_platform_membership(db, _user_id(db, user["email"]), role=role)
    return user


def _team_id(db: Session, slug: str) -> uuid.UUID:
    team = db.scalar(select(GovernanceTeam).where(GovernanceTeam.slug == slug))
    assert team is not None
    return team.id


# --- 1. SLA determinism -------------------------------------------------------------

def test_sla_state_function_is_deterministic():
    now = utc_now_naive()

    def make(**kw):
        return GovernanceReport(
            reporter_user_id=uuid.uuid4(),
            target_type="conversation",
            target_id=str(uuid.uuid4()),
            category="abuse",
            severity="high",
            priority=kw.pop("priority", "normal"),
            status=kw.pop("status", "open"),
            description="x",
            **kw,
        )

    # Fresh open case: on track.
    fresh = make()
    assert sla_state_for(fresh, now) == SLA_STATE_ON_TRACK

    # Response deadline in the past with no first response -> breached.
    late_response = make()
    late_response.sla_response_due_at = now - timedelta(minutes=1)
    assert sla_state_for(late_response, now) == SLA_STATE_BREACHED

    # Resolution deadline past while open -> breached.
    late_resolution = make()
    late_resolution.sla_response_due_at = now - timedelta(minutes=1)
    late_resolution.first_responded_at = now - timedelta(hours=1)
    late_resolution.sla_resolution_due_at = now - timedelta(minutes=1)
    assert sla_state_for(late_resolution, now) == SLA_STATE_BREACHED

    # Responded, resolution due within 2h -> due soon.
    soon = make()
    soon.sla_response_due_at = now - timedelta(hours=1)
    soon.first_responded_at = now - timedelta(hours=1)
    soon.sla_resolution_due_at = now + timedelta(minutes=30)
    assert sla_state_for(soon, now) == SLA_STATE_DUE_SOON

    # Resolved cases are never breached.
    done = make(status="resolved")
    done.sla_resolution_due_at = now - timedelta(hours=5)
    assert sla_state_for(done, now) == SLA_STATE_ON_TRACK

    # Windows match the priority policy exactly.
    critical = make(priority=REPORT_PRIORITY_CRITICAL)
    assert REPORT_SLA_HOURS[critical.priority][0] == 1  # response
    assert REPORT_SLA_HOURS[critical.priority][1] == 8  # resolution


def test_priority_change_restarts_sla_deadlines(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    report = _file_report(client, make_user(f"cand-{uuid.uuid4().hex[:6]}@example.com"))

    row = db.get(GovernanceReport, uuid.UUID(report["id"]))
    assert row is not None
    assert row.priority == "normal"
    assert row.sla_response_due_at is not None
    assert row.sla_resolution_due_at is not None
    assert row.sla_resolution_due_at - row.sla_response_due_at > timedelta(hours=1)

    changed = client.post(
        f"/api/v1/governance/reports/{report['id']}/priority",
        headers=moderator["authorization"],
        json={"priority": "critical"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["priority"] == "critical"
    assert changed.json()["sla_state"] == SLA_STATE_ON_TRACK

    db.expire_all()  # drop the identity-map cache written before the API call
    refreshed = db.get(GovernanceReport, uuid.UUID(report["id"]))
    resp_h, resol_h = REPORT_SLA_HOURS[REPORT_PRIORITY_CRITICAL]
    now = utc_now_naive()
    # Restart from the change time: response due ~now+1h, resolution ~now+8h.
    assert abs((refreshed.sla_response_due_at - now).total_seconds() / 3600 - resp_h) < 0.01
    assert abs((refreshed.sla_resolution_due_at - now).total_seconds() / 3600 - resol_h) < 0.01

    # Priority change is audited with from/to (reference only).
    audit = db.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.resource_id == str(report["id"]),
            AuditLogEntry.action == "governance.report.priority_changed",
        )
    ).all()
    assert len(audit) == 1
    assert audit[0].payload["from_priority"] == "normal"
    assert audit[0].payload["to_priority"] == "critical"

    # And an org-scope governance event exists with metadata only.
    events = db.scalars(
        select(PlatformEvent).where(
            PlatformEvent.event_type == "governance.case.priority_changed",
            PlatformEvent.resource_id == str(report["id"]),
        )
    ).all()
    assert len(events) == 1
    assert "description" not in events[0].payload


# --- 2. Escalation -------------------------------------------------------------------

def test_escalation_is_explicit_audited_and_safe(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    second = _moderator(client, make_user, db)
    candidate = make_user(f"esc-cand-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(client, candidate)

    # Assign to the second moderator, then escalate by the first.
    assigned = client.post(
        f"/api/v1/governance/reports/{report['id']}/assign",
        headers=moderator["authorization"],
        json={"moderator_user_id": str(_user_id(db, second["email"]))},
    )
    assert assigned.status_code == 200, assigned.text

    reason = "Urgent escalation: pattern matches other open cases in this region."
    escalated = client.post(
        f"/api/v1/governance/reports/{report['id']}/escalate",
        headers=moderator["authorization"],
        json={"reason": reason, "priority": "critical", "severity": "high"},
    )
    assert escalated.status_code == 200, escalated.text
    body = escalated.json()
    assert body["status"] == "escalated"
    assert body["priority"] == "critical"
    assert body["escalated_at"] is not None

    # A bare status flip to escalated is refused (must use the escalate action).
    flip = client.patch(
        f"/api/v1/governance/reports/{report['id']}/status",
        headers=moderator["authorization"],
        json={"status": "escalated"},
    )
    assert flip.status_code == 422

    # Audit records the escalation WITHOUT the reason body (reference only).
    audit = db.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.action == "governance.report.escalated",
            AuditLogEntry.resource_id == str(report["id"]),
        )
    ).all()
    assert len(audit) == 1
    blob = str(audit[0].payload or {})
    assert reason not in blob
    assert audit[0].payload["reason_present"] is True

    # The assignee was notified (governance kind, no case content).
    notification = db.scalar(
        select(UserNotification).where(
            UserNotification.user_id == _user_id(db, second["email"])
        )
    )
    assert notification is not None

    # Event carries metadata only.
    events = db.scalars(
        select(PlatformEvent).where(
            PlatformEvent.event_type == "governance.case.escalated",
            PlatformEvent.resource_id == str(report["id"]),
        )
    ).all()
    assert len(events) == 1
    assert "description" not in events[0].payload
    assert "reason" not in events[0].payload

    # Auditors can read but NOT escalate.
    auditor = _moderator(client, make_user, db, role="governance_auditor")
    denied = client.post(
        f"/api/v1/governance/reports/{report['id']}/escalate",
        headers=auditor["authorization"],
        json={"reason": "Trying to escalate without permission."},
    )
    assert denied.status_code == 403


# --- 3. Teams + team-aware assignment ------------------------------------------------

def test_team_membership_management_and_team_aware_assignment(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    team_mod = _moderator(client, make_user, db)
    outsider = _moderator(client, make_user, db)
    plain_user = make_user(f"plain-{uuid.uuid4().hex[:6]}@example.com")
    fraud_team = _team_id(db, "fraud")

    teams = client.get("/api/v1/governance/teams", headers=moderator["authorization"])
    assert teams.status_code == 200, teams.text
    assert teams.json()["total"] == 8

    # Only governance users can join; membership is audited.
    bad = client.post(
        f"/api/v1/governance/teams/{fraud_team}/members",
        headers=moderator["authorization"],
        json={"user_id": str(_user_id(db, plain_user["email"]))},
    )
    assert bad.status_code == 422
    ok = client.post(
        f"/api/v1/governance/teams/{fraud_team}/members",
        headers=moderator["authorization"],
        json={"user_id": str(_user_id(db, team_mod["email"]))},
    )
    assert ok.status_code == 201, ok.text
    audit = db.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.action == "governance.team.member_added"
        )
    ).all()
    assert len(audit) == 1

    # Auditors cannot manage teams (reports.teams absent).
    auditor = _moderator(client, make_user, db, role="governance_auditor")
    denied = client.post(
        f"/api/v1/governance/teams/{fraud_team}/members",
        headers=auditor["authorization"],
        json={"user_id": str(_user_id(db, outsider["email"]))},
    )
    assert denied.status_code == 403

    # Route a case to the fraud team, then try assignments.
    candidate = make_user(f"team-cand-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(client, candidate, category="fraud")
    routed = client.post(
        f"/api/v1/governance/reports/{report['id']}/team",
        headers=moderator["authorization"],
        json={"team_id": str(fraud_team)},
    )
    assert routed.status_code == 200, routed.text
    assert routed.json()["team_name"] == "Fraud"

    # Outsider is NOT on the team -> refused.
    bad_assign = client.post(
        f"/api/v1/governance/reports/{report['id']}/assign",
        headers=moderator["authorization"],
        json={"moderator_user_id": str(_user_id(db, outsider["email"]))},
    )
    assert bad_assign.status_code == 422
    # Team member -> allowed.
    good_assign = client.post(
        f"/api/v1/governance/reports/{report['id']}/assign",
        headers=moderator["authorization"],
        json={"moderator_user_id": str(_user_id(db, team_mod["email"]))},
    )
    assert good_assign.status_code == 200, good_assign.text
    assert good_assign.json()["assigned_moderator_id"] == str(_user_id(db, team_mod["email"]))

    # Team detail shows members + workload counts.
    detail = client.get(
        f"/api/v1/governance/teams/{fraud_team}",
        headers=moderator["authorization"],
    )
    assert detail.status_code == 200
    assert any(m["user_id"] == str(_user_id(db, team_mod["email"])) for m in detail.json()["members"])
    assert detail.json()["counts"]["open"] >= 1

    # Remove member (audited); the membership row is gone.
    removed = client.delete(
        f"/api/v1/governance/teams/{fraud_team}/members/{str(_user_id(db, team_mod['email']))}",
        headers=moderator["authorization"],
    )
    assert removed.status_code == 200
    db.expire_all()
    membership_row = db.scalar(
        select(GovernanceTeamMember).where(
            GovernanceTeamMember.team_id == fraud_team,
            GovernanceTeamMember.user_id == _user_id(db, team_mod["email"]),
        )
    )
    assert membership_row is None


# --- 4. Case links + tenant boundary ---------------------------------------------------

def test_case_links_respect_tenant_boundaries(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    org_admin = make_user(f"link-admin-{uuid.uuid4().hex[:6]}@example.com")
    org_a = _make_employer_membership(db, _user_id(db, org_admin["email"]))
    org_b = _make_employer_membership(db, _user_id(db, org_admin["email"]))
    reporter = make_user(f"link-cand-{uuid.uuid4().hex[:6]}@example.com")

    r1 = _file_report(client, reporter, organization_id=str(org_a))
    r2 = _file_report(client, reporter, organization_id=str(org_a))
    r_other = _file_report(client, reporter, organization_id=str(org_b))

    # Same-tenant link is allowed and audited.
    linked = client.post(
        f"/api/v1/governance/reports/{r1['id']}/links",
        headers=moderator["authorization"],
        json={"report_id": r2["id"], "reason": "Same incident, two reports."},
    )
    assert linked.status_code == 201, linked.text

    # Self-link refused.
    self_link = client.post(
        f"/api/v1/governance/reports/{r1['id']}/links",
        headers=moderator["authorization"],
        json={"report_id": r1["id"]},
    )
    assert self_link.status_code == 422

    # Cross-tenant link refused.
    cross = client.post(
        f"/api/v1/governance/reports/{r1['id']}/links",
        headers=moderator["authorization"],
        json={"report_id": r_other["id"]},
    )
    assert cross.status_code == 422

    # Detail surfaces the link (case refs only) and audit recorded it.
    detail = client.get(
        f"/api/v1/governance/reports/{r1['id']}",
        headers=moderator["authorization"],
    ).json()
    assert len(detail["links"]) == 1
    assert detail["links"][0]["report_id"] == r2["id"]
    audit = db.scalars(
        select(AuditLogEntry).where(
            AuditLogEntry.action == "governance.report.linked",
            AuditLogEntry.resource_id == str(r1["id"]),
        )
    ).all()
    assert len(audit) == 1

    # Unlink works and is audited.
    link_id = db.scalar(
        select(GovernanceCaseLink.id).where(
            GovernanceCaseLink.case_id == uuid.UUID(r1["id"])
        )
    )
    unlinked = client.delete(
        f"/api/v1/governance/reports/{r1['id']}/links/{link_id}",
        headers=moderator["authorization"],
    )
    assert unlinked.status_code == 200
    detail2 = client.get(
        f"/api/v1/governance/reports/{r1['id']}",
        headers=moderator["authorization"],
    ).json()
    assert detail2["links"] == []


# --- 5. Queue views + dashboard -----------------------------------------------------------

def test_queue_views_and_operational_dashboard(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    second = _moderator(client, make_user, db)
    reporter = make_user(f"q-cand-{uuid.uuid4().hex[:6]}@example.com")

    report = _file_report(client, reporter)
    client.post(
        f"/api/v1/governance/reports/{report['id']}/assign",
        headers=second["authorization"],
        json={},
    )

    dash = client.get(
        "/api/v1/governance/dashboard", headers=moderator["authorization"]
    ).json()
    assert dash["total"] >= 1
    assert dash["open"] >= 1
    assert dash["unassigned"] >= 0
    assert "by_priority" in dash
    assert "by_category" in dash
    assert "by_team" in dash
    assert "breached" in dash and "due_soon" in dash and "escalated" in dash

    # Views: mine shows only cases assigned to me (second moderator).
    mine = client.get(
        "/api/v1/governance/reports?mine=true", headers=second["authorization"]
    ).json()
    assert mine["total"] >= 1
    assert all(
        i["assigned_moderator_id"] == str(_user_id(db, second["email"]))
        for i in mine["items"]
    )
    # The first moderator's "mine" does not include second's case.
    not_mine = client.get(
        "/api/v1/governance/reports?mine=true", headers=moderator["authorization"]
    ).json()
    assert all(
        i["assigned_moderator_id"] != str(_user_id(db, second["email"]))
        for i in not_mine["items"]
    )

    # Unassigned view (new report never assigned).
    fresh = _file_report(client, reporter)
    unassigned = client.get(
        "/api/v1/governance/reports?unassigned=true",
        headers=moderator["authorization"],
    ).json()
    assert any(i["id"] == fresh["id"] for i in unassigned["items"])

    # Sorting + filters are server-side.
    sorted_page = client.get(
        "/api/v1/governance/reports?sort=created_at&page_size=5",
        headers=moderator["authorization"],
    ).json()
    assert len(sorted_page["items"]) <= 5


# --- 6. Audit review ------------------------------------------------------------------------

def test_audit_review_filters_paginates_and_sanitizes(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    auditor = _moderator(client, make_user, db, role="governance_auditor")
    employer = make_user(f"ar-emp-{uuid.uuid4().hex[:6]}@example.com")
    _make_employer_membership(db, _user_id(db, employer["email"]))

    candidate = make_user(f"ar-cand-{uuid.uuid4().hex[:6]}@example.com")
    secret_password = "SuperSecretValue99!"
    report = _file_report(client, candidate)
    reason = "Audit probe escalation reason that must never appear in review."
    client.post(
        f"/api/v1/governance/reports/{report['id']}/escalate",
        headers=moderator["authorization"],
        json={"reason": reason, "priority": "urgent"},
    )
    # A password lifecycle event anywhere must never surface in review.
    client.post(
        "/api/v1/auth/change-password",
        headers=candidate["authorization"],
        json={
            "current_password": candidate["password"],
            "new_password": secret_password,
        },
    )

    # Employer: 403 on the audit review surface.
    assert (
        client.get("/api/v1/governance/audit", headers=employer["authorization"]).status_code
        == 403
    )

    # Auditor can read; filters work.
    review = client.get(
        "/api/v1/governance/audit?action_prefix=governance.&page_size=50",
        headers=auditor["authorization"],
    )
    assert review.status_code == 200, review.text
    body = review.json()
    assert body["total"] >= 1
    actions = [i["action"] for i in body["items"]]
    assert "governance.report.escalated" in actions

    # Sanitization: no secrets, no reason text, no message bodies.
    for item in body["items"]:
        payload = item["payload"] or {}
        for key in ("password", "token", "body", "secret"):
            assert key not in payload
        blob = str(payload)
        assert secret_password not in blob
        assert reason not in blob

    # Actor/resource filters are bounded and honest.
    filtered = client.get(
        f"/api/v1/governance/audit?resource_id={report['id']}&page_size=5",
        headers=auditor["authorization"],
    ).json()
    assert filtered["total"] >= 1
    assert all(i["resource_id"] == report["id"] for i in filtered["items"])


# --- 7. Integrity signals ----------------------------------------------------------------------

def test_integrity_signals_neutral_and_gated(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    employer = make_user(f"sig-emp-{uuid.uuid4().hex[:6]}@example.com")
    _make_employer_membership(db, _user_id(db, employer["email"]))

    # Employers never see signals.
    assert (
        client.get("/api/v1/governance/signals", headers=employer["authorization"]).status_code
        == 403
    )

    # One reporter files five reports -> a neutral repeated_reports signal.
    reporter = make_user(f"sig-cand-{uuid.uuid4().hex[:6]}@example.com")
    for _ in range(5):
        _file_report(client, reporter)

    signals = client.get(
        "/api/v1/governance/signals", headers=moderator["authorization"]
    ).json()
    repeated = [s for s in signals["items"] if s["signal_type"] == "repeated_reports"]
    assert len(repeated) >= 1
    signal = repeated[0]
    assert signal["count"] >= 5
    # Neutral terminology only — never an accusation.
    note = signal["note"].lower()
    for word in ("fraudulent", "deceptive", "malicious", "lying"):
        assert word not in note
    assert "review" in note


# --- 8. Reopen restarts SLA + governance never opens private Work ID -----------------------------

def test_reopen_restarts_sla_and_is_audited(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    candidate = make_user(f"re-cand-{uuid.uuid4().hex[:6]}@example.com")
    report = _file_report(client, candidate)

    resolved = client.post(
        f"/api/v1/governance/reports/{report['id']}/resolve",
        headers=moderator["authorization"],
        json={"resolution": "Reviewed and closed with a warning to the org."},
    )
    assert resolved.status_code == 200
    reopened = client.post(
        f"/api/v1/governance/reports/{report['id']}/reopen",
        headers=moderator["authorization"],
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "in_review"
    assert reopened.json()["reopened_count"] == 1
    assert reopened.json()["sla_state"] == SLA_STATE_ON_TRACK

    row = db.get(GovernanceReport, uuid.UUID(report["id"]))
    assert row.resolved_at is None
    resp_h, resol_h = REPORT_SLA_HOURS[row.priority]
    # Resolution deadline restarted at reopen: still in the future.
    assert row.sla_resolution_due_at > utc_now_naive()

    events = db.scalars(
        select(PlatformEvent).where(
            PlatformEvent.event_type == "governance.case.reopened",
            PlatformEvent.resource_id == str(report["id"]),
        )
    ).all()
    assert len(events) == 1
    assert events[0].payload == {"reopened_count": 1}


def test_governance_surfaces_never_contain_private_work_id(client, make_user, db):
    moderator = _moderator(client, make_user, db)
    candidate = make_user(f"priv-cand-{uuid.uuid4().hex[:6]}@example.com")
    # Give the candidate a private phone + headline so we can prove non-leak.
    client.put(
        "/api/v1/work-id/profile",
        headers=candidate["authorization"],
        json={"headline": "Private headliner", "phone": "+971500000000"},
    )
    report = _file_report(
        client, candidate, target_type="person_profile",
        category="other",
        description="A person-profile concern requires case review.",
    )

    # Queue + detail + signals never echo the person's private fields.
    for path in (
        "/api/v1/governance/reports",
        f"/api/v1/governance/reports/{report['id']}",
        "/api/v1/governance/signals",
    ):
        response = client.get(path, headers=moderator["authorization"])
        assert response.status_code == 200
        assert "+971500000000" not in response.text
        assert "Private headliner" not in response.text


# --- 9. Tenant / role isolation on Phase 10 surfaces -------------------------------------------

def test_phase10_surfaces_denied_to_non_governance_roles(client, make_user, db):
    surfaces = [
        ("GET", "/api/v1/governance/teams"),
        ("GET", "/api/v1/governance/audit"),
        ("GET", "/api/v1/governance/signals"),
        ("GET", "/api/v1/governance/moderators"),
    ]
    # Employer, recruiter, candidate, government.
    employer = make_user(f"deny-emp-{uuid.uuid4().hex[:6]}@example.com")
    _make_employer_membership(db, _user_id(db, employer["email"]))
    gov = make_user(f"deny-gov-{uuid.uuid4().hex[:6]}@example.com")
    _make_government_membership(db, _user_id(db, gov["email"]))
    candidate = make_user(f"deny-cand-{uuid.uuid4().hex[:6]}@example.com")

    for method, path in surfaces:
        for user in (employer, gov, candidate):
            response = client.request(method, path, headers=user["authorization"])
            assert response.status_code == 403, (path, response.status_code)
