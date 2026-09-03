"""Phase 8 — Controlled Talent Outreach & Communication tests.

Security targets from the brief:
- DISCOVER -> REQUEST -> CONSENT -> CONNECT -> COMMUNICATE -> APPLY.
- Sending an outreach request NEVER reveals private contact details; a
  decline gives the company a GENERIC outcome; accepting opens a controlled
  in-platform conversation only.
- Company A can never see Company B's outreach/conversations/messages; a
  recruiter cannot reach another org's rows by knowing a UUID.
- Candidate stays in control: accept / decline / report / block.
- Abuse controls: duplicate-pending prevention, cooldown after any request,
  standing blocks, expiry.
- RBAC: granular (outreach vs communications permissions per role).
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.timeutil import utc_now_naive
from app.models.career import JobApplication, UserNotification
from app.models.communication import (
    Conversation,
    ConversationMessage,
    OutreachRequest,
)
from app.models.enums import NOTIFICATION_KIND_OUTREACH
from app.models.identity import PersonProfile, User


# --- helpers ------------------------------------------------------------------

def _create_company(client: TestClient, admin, name: str, slug: str) -> dict:
    response = client.post(
        "/api/v1/organizations",
        headers=admin["authorization"],
        json={"name": name, "slug": slug, "kind": "employer"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _add_member(client: TestClient, admin, org_id: str, email: str, role: str) -> None:
    response = client.post(
        f"/api/v1/organizations/{org_id}/members",
        headers=admin["authorization"],
        json={"user_email": email, "role": role},
    )
    assert response.status_code == 201, response.text


def _add_skill(client: TestClient, user, skill_name: str) -> None:
    response = client.put(
        "/api/v1/work-id/skills",
        headers=user["authorization"],
        json={"skill_name": skill_name, "level": "advanced", "years_experience": 5},
    )
    assert response.status_code == 200, response.text


def _make_discoverable(client: TestClient, user) -> None:
    response = client.put(
        "/api/v1/work-id/privacy",
        headers=user["authorization"],
        json={
            "settings": {
                "profile": "public", "skills": "public",
                "experience": "public", "education": "public",
            }
        },
    )
    assert response.status_code == 200, response.text


def _publish_job(client: TestClient, admin, org_id: str, **overrides) -> dict:
    payload = {
        "title": "Frontend Engineer",
        "summary": "Build product UI.",
        "skills_required": ["React", "TypeScript"],
        "experience_level": "2+ years",
        "work_mode": "hybrid",
        "employment_type": "full_time",
        "seniority": "mid",
        "country": "AE",
        "city": "Dubai",
    }
    payload.update(overrides)
    job = client.post(
        f"/api/v1/company/{org_id}/jobs",
        headers=admin["authorization"],
        json=payload,
    )
    assert job.status_code == 201, job.text
    published = client.post(
        f"/api/v1/company/{org_id}/jobs/{job.json()['id']}/publish",
        headers=admin["authorization"],
    )
    assert published.status_code == 200, published.text
    return published.json()


def _candidate_person_id(db: Session, email: str) -> str:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    person = db.scalar(select(PersonProfile).where(PersonProfile.user_id == user.id))
    return str(person.id)


def _send_outreach(
    client: TestClient,
    admin,
    org_id: str,
    person_id: str,
    opportunity_id=None,
    message="We found your profile compelling and would like to discuss a role.",
) -> dict:
    payload = {"person_id": person_id, "message": message}
    if opportunity_id:
        payload["opportunity_id"] = opportunity_id
    response = client.post(
        f"/api/v1/talent/{org_id}/outreach",
        headers=admin["authorization"],
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- 1. Happy path --------------------------------------------------------------

def test_full_outreach_to_conversation_flow(client, make_user, db):
    admin = make_user(f"flow-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Flow Co", f"flow-{uuid.uuid4().hex[:6]}")
    published = _publish_job(client, admin, org["id"])
    opp_id = published["opportunity_id"]

    candidate = make_user(f"flow-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    client.put(
        "/api/v1/work-id/profile",
        headers=candidate["authorization"],
        json={"headline": "Frontend engineer", "phone": "+971555000111"},
    )
    person_id = _candidate_person_id(db, candidate["email"])

    # 1. Recruiter requests contact.
    sent = _send_outreach(client, admin, org["id"], person_id, opportunity_id=opp_id)
    assert sent["status"] == "sent"
    assert sent["candidate"]["person_id"] == person_id
    # No private contact details in the request payload, ever.
    assert "phone" not in str(sent)
    assert "email" not in str(sent)
    request_id = sent["id"]

    # Candidate is notified (outreach kind) and sees the request.
    note = db.scalar(
        select(UserNotification).where(
            UserNotification.user_id == _candidate_user_id(db, person_id),
            UserNotification.kind == NOTIFICATION_KIND_OUTREACH,
        )
    )
    assert note is not None
    inbox = client.get(
        "/api/v1/jobseeker/communications", headers=candidate["authorization"]
    ).json()
    assert any(r["id"] == request_id for r in inbox["outreach"])

    # 2. Candidate views (marks viewed) and accepts.
    viewed = client.get(
        f"/api/v1/jobseeker/outreach/{request_id}",
        headers=candidate["authorization"],
    ).json()
    assert viewed["status"] == "viewed"
    accepted = client.post(
        f"/api/v1/jobseeker/outreach/{request_id}/accept",
        headers=candidate["authorization"],
    )
    assert accepted.status_code == 200, accepted.text
    conv_id = accepted.json()["conversation_id"]

    # The org sees the acceptance; a controlled conversation now exists.
    org_outreach = client.get(
        f"/api/v1/talent/{org['id']}/outreach", headers=admin["authorization"]
    ).json()
    assert any(r["id"] == request_id and r["status"] == "accepted" for r in org_outreach)

    # 3. Recruiter sends a message; candidate replies.
    msg = client.post(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}/messages",
        headers=admin["authorization"],
        json={"body": "Thanks for accepting — when suits for a first call?"},
    )
    assert msg.status_code == 201, msg.text

    conv_for_candidate = client.get(
        f"/api/v1/jobseeker/communications/{conv_id}",
        headers=candidate["authorization"],
    ).json()
    assert len(conv_for_candidate["messages"]) == 1
    assert conv_for_candidate["messages"][0]["sender_side"] == "recruiter"

    reply = client.post(
        f"/api/v1/jobseeker/communications/{conv_id}/messages",
        headers=candidate["authorization"],
        json={"body": "This week works well — Thursday morning?"},
    )
    assert reply.status_code == 201, reply.text

    # 4. The recruiter sees both messages, marks read, and unread clears.
    before_read = client.get(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}",
        headers=admin["authorization"],
    ).json()
    assert len(before_read["messages"]) == 2
    assert before_read["unread_count"] >= 1  # candidate's reply is unread for them
    read = client.post(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}/read",
        headers=admin["authorization"],
    )
    assert read.status_code == 200
    after_read = client.get(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}",
        headers=admin["authorization"],
    ).json()
    assert after_read["unread_count"] == 0

    # Message bodies never include private contact data.
    assert "555000111" not in str(after_read)

    # 5. Candidate closes the conversation.
    closed = client.post(
        f"/api/v1/jobseeker/communications/{conv_id}/close",
        headers=candidate["authorization"],
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    send_after_close = client.post(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}/messages",
        headers=admin["authorization"],
        json={"body": "Hello?"},
    )
    assert send_after_close.status_code == 422


def _candidate_user_id(db: Session, person_id: str):
    person = db.get(PersonProfile, uuid.UUID(person_id))
    return person.user_id if person else None


# --- 2. Candidate privacy + control ----------------------------------------------

def test_outreach_to_non_visible_candidate_hidden(client, make_user, db):
    admin = make_user(f"priv-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Privacy Co", f"priv-{uuid.uuid4().hex[:6]}")
    candidate = make_user(f"priv-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    # Profile stays PRIVATE (default) and there is no application -> the org
    # cannot see the person, so the outreach is a 404 (existence hidden).
    person_id = _candidate_person_id(db, candidate["email"])
    response = client.post(
        f"/api/v1/talent/{org['id']}/outreach",
        headers=admin["authorization"],
        json={"person_id": person_id, "message": "We would like to contact you."},
    )
    assert response.status_code == 404


def test_pipeline_candidate_is_outreachable_with_application_link(
    client, make_user, db
):
    admin = make_user(f"pipe-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Pipe Co", f"pipe-{uuid.uuid4().hex[:6]}")
    published = _publish_job(client, admin, org["id"])
    opp_id = published["opportunity_id"]

    candidate = make_user(f"pipe-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    # Private profile but a live application -> legitimately visible to the org.
    app = client.post(
        "/api/v1/jobseeker/applications",
        headers=candidate["authorization"],
        json={"opportunity_id": opp_id},
    )
    assert app.status_code == 201, app.text
    app_id = app.json()["id"]
    person_id = _candidate_person_id(db, candidate["email"])

    sent = _send_outreach(client, admin, org["id"], person_id, opportunity_id=opp_id)
    assert sent["application_id"] == app_id

    accepted = client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/accept",
        headers=candidate["authorization"],
    ).json()
    conv = client.get(
        f"/api/v1/talent/{org['id']}/communications/{accepted['conversation_id']}",
        headers=admin["authorization"],
    ).json()
    assert conv["application_id"] == app_id
    assert conv["opportunity_id"] == opp_id

    # The application lifecycle is untouched: still the canonical row.
    app_row = db.get(JobApplication, uuid.UUID(app_id))
    assert app_row is not None and app_row.status == "applied"


def test_decline_is_generic_and_no_conversation_opens(client, make_user, db):
    admin = make_user(f"decl-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Decline Co", f"decl-{uuid.uuid4().hex[:6]}")
    candidate = make_user(f"decl-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    sent = _send_outreach(client, admin, org["id"], person_id)
    declined = client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/decline",
        headers=candidate["authorization"],
        json={"note": "Not currently exploring opportunities."},
    )
    assert declined.status_code == 200
    assert declined.json()["status"] == "declined"

    # No conversation was created.
    assert db.scalar(select(Conversation.id).limit(1)) is None
    # Company sees only the generic outcome, never the note content.
    org_view = client.get(
        f"/api/v1/talent/{org['id']}/outreach", headers=admin["authorization"]
    ).json()
    row = next(r for r in org_view if r["id"] == sent["id"])
    assert row["status"] == "declined"


# --- 3. Abuse controls ------------------------------------------------------------

def test_duplicate_and_cooldown_controls(client, make_user, db):
    admin = make_user(f"abuse-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Abuse Co", f"abuse-{uuid.uuid4().hex[:6]}")
    candidate = make_user(f"abuse-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    sent = _send_outreach(client, admin, org["id"], person_id)
    # Duplicate pending -> 409.
    dup = client.post(
        f"/api/v1/talent/{org['id']}/outreach",
        headers=admin["authorization"],
        json={"person_id": person_id, "message": "Second attempt immediately."},
    )
    assert dup.status_code == 409

    # Candidate declines; immediate re-send still blocked by the cooldown.
    client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/decline",
        headers=candidate["authorization"],
    )
    retry = client.post(
        f"/api/v1/talent/{org['id']}/outreach",
        headers=admin["authorization"],
        json={"person_id": person_id, "message": "Trying again right away."},
    )
    assert retry.status_code == 409


def test_blocked_organization_cannot_outreach_again(client, make_user, db):
    admin = make_user(f"block-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Blocked Co", f"blocked-{uuid.uuid4().hex[:6]}")
    candidate = make_user(f"block-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    sent = _send_outreach(client, admin, org["id"], person_id)
    blocked = client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/report",
        headers=candidate["authorization"],
        json={"note": "Unsolicited and irrelevant."},
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "blocked"

    # The org now appears on the candidate's block list.
    blocks = client.get(
        "/api/v1/jobseeker/communications/blocks",
        headers=candidate["authorization"],
    ).json()
    assert any(b["organization_id"] == org["id"] for b in blocks)

    # A brand-new request attempt is refused (403), not merely rate limited.
    denied = client.post(
        f"/api/v1/talent/{org['id']}/outreach",
        headers=admin["authorization"],
        json={"person_id": person_id, "message": "Please reconsider."},
    )
    assert denied.status_code == 403

    # Candidate unblocks the org (their own decision).
    removed = client.delete(
        f"/api/v1/jobseeker/communications/organizations/{org['id']}/block",
        headers=candidate["authorization"],
    )
    assert removed.status_code == 200
    assert client.get(
        "/api/v1/jobseeker/communications/blocks",
        headers=candidate["authorization"],
    ).json() == []


def test_expired_outreach_cannot_be_accepted(client, make_user, db):
    admin = make_user(f"exp-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Expire Co", f"exp-{uuid.uuid4().hex[:6]}")
    candidate = make_user(f"exp-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    sent = _send_outreach(client, admin, org["id"], person_id)
    request = db.get(OutreachRequest, uuid.UUID(sent["id"]))
    request.expires_at = utc_now_naive() - timedelta(days=1)
    db.commit()

    response = client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/accept",
        headers=candidate["authorization"],
    )
    assert response.status_code == 422
    assert db.scalar(select(Conversation.id).limit(1)) is None


# --- 4. Tenant isolation + RBAC ----------------------------------------------------

def test_cross_tenant_outreach_and_conversation_isolation(client, make_user, db):
    admin_a = make_user(f"iso8-a-{uuid.uuid4().hex[:6]}@example.com")
    org_a = _create_company(client, admin_a, "Iso8 A Co", f"iso8a-{uuid.uuid4().hex[:6]}")
    admin_b = make_user(f"iso8-b-{uuid.uuid4().hex[:6]}@example.com")
    _create_company(client, admin_b, "Iso8 B Co", f"iso8b-{uuid.uuid4().hex[:6]}")

    candidate = make_user(f"iso8-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    sent = _send_outreach(client, admin_a, org_a["id"], person_id)
    accepted = client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/accept",
        headers=candidate["authorization"],
    ).json()
    conv_id = accepted["conversation_id"]

    # Company B is a member of its own org only: every A-scoped route is 403,
    # even knowing the exact conversation UUID.
    for path in [
        f"/api/v1/talent/{org_a['id']}/outreach",
        f"/api/v1/talent/{org_a['id']}/outreach/{sent['id']}",
        f"/api/v1/talent/{org_a['id']}/communications",
        f"/api/v1/talent/{org_a['id']}/communications/{conv_id}",
    ]:
        response = client.get(path, headers=admin_b["authorization"])
        assert response.status_code == 403, path

    message = client.post(
        f"/api/v1/talent/{org_a['id']}/communications/{conv_id}/messages",
        headers=admin_b["authorization"],
        json={"body": "Hi from B"},
    )
    assert message.status_code == 403

    # Another candidate cannot see this conversation either (404).
    stranger = make_user(f"iso8-stranger-{uuid.uuid4().hex[:6]}@example.com")
    hidden = client.get(
        f"/api/v1/jobseeker/communications/{conv_id}",
        headers=stranger["authorization"],
    )
    assert hidden.status_code == 404
    # Nor another candidate's outreach.
    other_outreach = client.get(
        f"/api/v1/jobseeker/outreach/{sent['id']}",
        headers=stranger["authorization"],
    )
    assert other_outreach.status_code == 404


def test_rbac_recruiter_vs_hiring_manager_communications(client, make_user, db):
    admin = make_user(f"rbac8-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Rbac8 Co", f"rbac8-{uuid.uuid4().hex[:6]}")
    recruiter = make_user(f"rbac8-rec-{uuid.uuid4().hex[:6]}@example.com")
    _add_member(client, admin, org["id"], recruiter["email"], "recruiter")
    hiring = make_user(f"rbac8-hm-{uuid.uuid4().hex[:6]}@example.com")
    _add_member(client, admin, org["id"], hiring["email"], "hiring_manager")

    candidate = make_user(f"rbac8-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    # Recruiter CAN create outreach; hiring manager CANNOT.
    sent = _send_outreach(client, recruiter, org["id"], person_id)
    denied = client.post(
        f"/api/v1/talent/{org['id']}/outreach",
        headers=hiring["authorization"],
        json={"person_id": person_id, "message": "We would like to contact you."},
    )
    assert denied.status_code == 403

    accepted = client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/accept",
        headers=candidate["authorization"],
    ).json()
    conv_id = accepted["conversation_id"]

    # Hiring manager may READ the conversation (communications.read)...
    conv = client.get(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}",
        headers=hiring["authorization"],
    )
    assert conv.status_code == 200
    # ...but cannot SEND (no communications.send) nor close (no manage).
    message = client.post(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}/messages",
        headers=hiring["authorization"],
        json={"body": "Hello"},
    )
    assert message.status_code == 403
    closed = client.post(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}/close",
        headers=hiring["authorization"],
    )
    assert closed.status_code == 403

    # A recruiter who is not the requester cannot cancel another's request
    # (recruiter role holds create/read but not manage).
    other_recruiter = make_user(f"rbac8-rec2-{uuid.uuid4().hex[:6]}@example.com")
    _add_member(client, admin, org["id"], other_recruiter["email"], "recruiter")
    cancel = client.post(
        f"/api/v1/talent/{org['id']}/outreach/{sent['id']}/cancel",
        headers=other_recruiter["authorization"],
    )
    assert cancel.status_code == 403


def test_org_opens_application_conversation_idempotently(client, make_user, db):
    admin = make_user(f"appc-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "App Conv Co", f"appc-{uuid.uuid4().hex[:6]}")
    published = _publish_job(client, admin, org["id"])
    opp_id = published["opportunity_id"]
    candidate = make_user(f"appc-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    app = client.post(
        "/api/v1/jobseeker/applications",
        headers=candidate["authorization"],
        json={"opportunity_id": opp_id},
    ).json()

    opened = client.post(
        f"/api/v1/talent/{org['id']}/communications",
        headers=admin["authorization"],
        json={"application_id": app["id"]},
    )
    assert opened.status_code == 201, opened.text
    conv_id = opened.json()["id"]

    again = client.post(
        f"/api/v1/talent/{org['id']}/communications",
        headers=admin["authorization"],
        json={"application_id": app["id"]},
    )
    assert again.status_code == 201
    assert again.json()["id"] == conv_id  # same thread, not a duplicate

    # A non-member org cannot open a conversation on an application it does
    # not own.
    intruder = make_user(f"appc-intruder-{uuid.uuid4().hex[:6]}@example.com")
    other_org = _create_company(client, intruder, "Intruder Co", f"appi-{uuid.uuid4().hex[:6]}")
    forbidden = client.post(
        f"/api/v1/talent/{other_org['id']}/communications",
        headers=intruder["authorization"],
        json={"application_id": app["id"]},
    )
    assert forbidden.status_code == 404


def test_read_state_is_per_user(client, make_user, db):
    admin = make_user(f"read-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Read Co", f"read-{uuid.uuid4().hex[:6]}")
    recruiter = make_user(f"read-rec-{uuid.uuid4().hex[:6]}@example.com")
    _add_member(client, admin, org["id"], recruiter["email"], "recruiter")

    candidate = make_user(f"read-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    sent = _send_outreach(client, admin, org["id"], person_id)
    conv_id = client.post(
        f"/api/v1/jobseeker/outreach/{sent['id']}/accept",
        headers=candidate["authorization"],
    ).json()["conversation_id"]

    # Candidate sends a message: admin (opener) and recruiter both unread.
    client.post(
        f"/api/v1/jobseeker/communications/{conv_id}/messages",
        headers=candidate["authorization"],
        json={"body": "Hi, thanks for reaching out."},
    )
    admin_view = client.get(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}",
        headers=admin["authorization"],
    ).json()
    assert admin_view["unread_count"] == 1
    rec_view = client.get(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}",
        headers=recruiter["authorization"],
    ).json()
    assert rec_view["unread_count"] == 1

    # Admin marks read — only the admin cursor moves.
    client.post(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}/read",
        headers=admin["authorization"],
    )
    assert client.get(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}",
        headers=admin["authorization"],
    ).json()["unread_count"] == 0
    assert client.get(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}",
        headers=recruiter["authorization"],
    ).json()["unread_count"] == 1
