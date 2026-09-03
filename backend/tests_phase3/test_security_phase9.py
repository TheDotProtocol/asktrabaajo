"""Phase 9 — Platform governance, realtime hardening & security tests.

Security targets from the brief (hostile paths assumed — attackers know UUIDs
and routes):

- Realtime events cannot cross tenants: Company B never sees Company A's
  events even knowing conversation/outreach UUIDs; org-scoped events reach
  only members of that org.
- Message events never leak message contents: event payloads are whitelisted
  metadata only, and message bodies never reach the event feed.
- Audit entries contain no secrets (passwords/tokens) and no raw message
  bodies.
- Rate limits activate correctly and their errors do not leak whether an
  account exists (identical generic 429 for existing and non-existent
  accounts).
"""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.ratelimit import RateLimiter
from app.models.audit import AuditLogEntry
from app.models.identity import PersonProfile, User
from app.models.platform import PlatformEvent


# --- helpers (mirror Phase 8 test helpers) ------------------------------------

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


def _candidate_person_id(db: Session, email: str) -> str:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    person = db.scalar(select(PersonProfile).where(PersonProfile.user_id == user.id))
    return str(person.id)


def _send_outreach(
    client: TestClient, admin, org_id: str, person_id: str, message: str
) -> dict:
    response = client.post(
        f"/api/v1/talent/{org_id}/outreach",
        headers=admin["authorization"],
        json={"person_id": person_id, "message": message},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run_conversation_flow(client: TestClient, make_user, db) -> dict:
    """Full DISCOVER->REQUEST->CONSENT->CONNECT->COMMUNICATE flow in org A.

    Returns the conversation_id and the raw message bodies sent.
    """
    admin = make_user(f"sec-admin-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "Sec Co", f"sec-{uuid.uuid4().hex[:6]}")

    candidate = make_user(f"sec-cand-{uuid.uuid4().hex[:6]}@example.com")
    _add_skill(client, candidate, "React")
    _make_discoverable(client, candidate)
    person_id = _candidate_person_id(db, candidate["email"])

    recruiter_text = "Thanks for accepting — when suits for a first call?"
    candidate_text = "This week works well — Thursday morning works."

    sent = _send_outreach(
        client, admin, org["id"], person_id,
        message="We found your profile compelling and would like to discuss a role.",
    )
    request_id = sent["id"]

    accepted = client.post(
        f"/api/v1/jobseeker/outreach/{request_id}/accept",
        headers=candidate["authorization"],
    )
    assert accepted.status_code == 200, accepted.text
    conv_id = accepted.json()["conversation_id"]

    msg = client.post(
        f"/api/v1/talent/{org['id']}/communications/{conv_id}/messages",
        headers=admin["authorization"],
        json={"body": recruiter_text},
    )
    assert msg.status_code == 201, msg.text

    reply = client.post(
        f"/api/v1/jobseeker/communications/{conv_id}/messages",
        headers=candidate["authorization"],
        json={"body": candidate_text},
    )
    assert reply.status_code == 201, reply.text

    return {
        "org": org,
        "admin": admin,
        "candidate": candidate,
        "conv_id": conv_id,
        "request_id": request_id,
        "recruiter_text": recruiter_text,
        "candidate_text": candidate_text,
    }


def _events_for(client: TestClient, user) -> list:
    response = client.get("/api/v1/events", headers=user["authorization"])
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _assert_no_message_bodies(events: list, bodies: list[str]) -> None:
    for event in events:
        payload = event.get("payload") or {}
        assert "body" not in payload, f"event leaked body key: {payload}"
        assert "text" not in payload, f"event leaked text key: {payload}"
        serialized = str(payload) + str(event.get("resource_id", ""))
        for body in bodies:
            assert body not in serialized, (
                f"event leaked message content: {payload}"
            )


# --- 1. Realtime event tenant isolation ----------------------------------------

def test_event_feed_never_crosses_tenants(client, make_user, db):
    admin_b = make_user(f"sec-b-admin-{uuid.uuid4().hex[:6]}@example.com")
    org_b = _create_company(client, admin_b, "Other Co", f"other-{uuid.uuid4().hex[:6]}")

    # A second member of org A (beyond the admin) must receive org-scoped
    # events, proving org-scope reaches members — and only members.
    member_a = make_user(f"sec-a-member-{uuid.uuid4().hex[:6]}@example.com")

    flow = _run_conversation_flow(client, make_user, db)
    org_a = flow["org"]
    _add_member(client, flow["admin"], org_a["id"], member_a["email"], "recruiter")

    # Company B sees nothing at all — not even knowing the conversation UUID.
    events_b = _events_for(client, admin_b)
    assert events_b == [], "Company B saw Company A events"

    # Candidate's feed: only events addressed to them (outreach.created,
    # recruiter's message.sent). The org-scoped events (outreach.accepted,
    # candidate's reply) must NOT appear — the candidate is not an org member.
    candidate_events = _events_for(client, flow["candidate"])
    types = [e["event_type"] for e in candidate_events]
    assert "outreach.created" in types
    assert "message.sent" in types
    assert "outreach.accepted" not in types, (
        "org-scoped event leaked to a non-member"
    )
    for event in candidate_events:
        if event["event_type"] == "message.sent":
            assert event["payload"]["sender_side"] == "recruiter"

    # Org A members see the org-scoped events (accept + candidate reply)…
    admin_a_events = _events_for(client, flow["admin"])
    member_a_events = _events_for(client, member_a)
    for feed in (admin_a_events, member_a_events):
        types = [e["event_type"] for e in feed]
        assert "outreach.accepted" in types
        assert "message.sent" in types
        for event in feed:
            if event["event_type"] == "message.sent":
                assert event["payload"]["sender_side"] == "candidate"
    # …and those events reference org A, never org B.
    for event in admin_a_events + member_a_events:
        if event.get("organization_id"):
            assert event["organization_id"] == org_a["id"]

    # Cross-tenant access by UUID is impossible: company B cannot open the
    # conversation, even though it knows the UUID (403 no-membership or 404
    # existence-hidden — both deny without leaking).
    hostile = client.get(
        f"/api/v1/talent/{org_b['id']}/communications/{flow['conv_id']}",
        headers=admin_b["authorization"],
    )
    assert hostile.status_code in (403, 404)


def test_events_never_leak_message_contents(client, make_user, db):
    flow = _run_conversation_flow(client, make_user, db)

    feeds = [
        _events_for(client, flow["admin"]),
        _events_for(client, flow["candidate"]),
    ]
    for feed in feeds:
        _assert_no_message_bodies(
            feed, [flow["recruiter_text"], flow["candidate_text"]]
        )
    # No event anywhere may carry a body-like key.
    rows = db.scalars(select(PlatformEvent)).all()
    for row in rows:
        payload = row.payload or {}
        assert "body" not in payload
        assert "text" not in payload


# --- 2. Audit hygiene -----------------------------------------------------------

def test_audit_rows_never_contain_secrets_or_message_bodies(client, make_user, db):
    flow = _run_conversation_flow(client, make_user, db)

    # Also run a password change so auth-related audit rows exist with a real
    # secret in flight.
    new_password = "FreshSecret123!"
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=flow["candidate"]["authorization"],
        json={
            "current_password": flow["candidate"]["password"],
            "new_password": new_password,
        },
    )
    assert changed.status_code == 200, changed.text

    rows = db.scalars(select(AuditLogEntry)).all()
    assert len(rows) >= 1
    secrets = [flow["candidate"]["password"], new_password]
    bodies = [flow["recruiter_text"], flow["candidate_text"]]
    for row in rows:
        payload = row.payload or {}
        for key in ("password", "new_password", "token", "body", "secret"):
            assert key not in payload, (
                f"audit payload leaked key '{key}': {payload} (action={row.action})"
            )
        blob = str(payload)
        for secret in secrets:
            assert secret not in blob, f"audit leaked a secret (action={row.action})"
        for body in bodies:
            assert body not in blob, f"audit leaked a message body (action={row.action})"


# --- 3. Rate limiting ------------------------------------------------------------

def test_login_rate_limit_activates_and_does_not_leak_account_existence(
    client, make_user
):
    user = make_user(f"sec-rl-{uuid.uuid4().hex[:6]}@example.com")

    # Tighten the login policy for this test's app instance only.
    client.app.state.rate_limiters["login"] = RateLimiter(
        max_requests=2, window_seconds=60
    )

    def attempt(email: str) -> dict:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "DefinitelyWrong123!"},
        )
        return {"status": response.status_code, "body": response.json()}

    # Existing account: two failures (401) then the limiter trips (429).
    first = attempt(user["email"])
    assert first["status"] == 401, first["body"]
    second = attempt(user["email"])
    assert second["status"] == 401, second["body"]
    third = attempt(user["email"])
    assert third["status"] == 429, third["body"]
    assert third["body"]["error"]["code"] == "rate_limited"

    # Non-existent account: identical generic 429 — no existence oracle.
    ghost = attempt(f"ghost-{uuid.uuid4().hex[:6]}@example.com")
    assert ghost["status"] == 429, ghost["body"]
    assert ghost["body"] == third["body"], (
        "rate-limit responses differ between existing and non-existing accounts"
    )


def test_outreach_rate_limit_trips_with_generic_error(client, make_user, db):
    admin = make_user(f"sec-rol-{uuid.uuid4().hex[:6]}@example.com")
    org = _create_company(client, admin, "RL Co", f"rl-{uuid.uuid4().hex[:6]}")
    # Each probe targets a DIFFERENT candidate so the org's duplicate-pending /
    # cooldown abuse guards never interfere — only the limiter can trip.
    candidates = []
    for i in range(3):
        candidate = make_user(f"sec-rol-cand-{uuid.uuid4().hex[:6]}@example.com")
        _add_skill(client, candidate, "React")
        _make_discoverable(client, candidate)
        candidates.append(_candidate_person_id(db, candidate["email"]))

    client.app.state.rate_limiters["outreach.create"] = RateLimiter(
        max_requests=2, window_seconds=60
    )

    for person_id in candidates[:2]:
        response = client.post(
            f"/api/v1/talent/{org['id']}/outreach",
            headers=admin["authorization"],
            json={"person_id": person_id, "message": "Rate-limit probe message."},
        )
        assert response.status_code == 201, response.text
    third = client.post(
        f"/api/v1/talent/{org['id']}/outreach",
        headers=admin["authorization"],
        json={"person_id": candidates[2], "message": "Rate-limit probe message."},
    )
    assert third.status_code == 429, third.text
    body = third.json()
    assert body["error"]["code"] == "rate_limited"
    # The 429 message is generic — it says nothing about the candidate/target.
    assert "candidate" not in body["error"]["message"].lower()
    assert "person" not in body["error"]["message"].lower()
