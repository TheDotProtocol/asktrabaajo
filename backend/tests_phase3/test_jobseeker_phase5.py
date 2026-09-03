"""Phase 5 — Jobseeker Career OS tests.

Coverage targets from the phase brief:
- work DNA ownership + validation
- opportunity discovery + explainable matching
- application lifecycle + state machine + timeline
- cross-user isolation on every career resource (404, existence hidden)
- interview privacy + reschedule policy
- offer privacy + decision flow
- advisor / dashboard on owned data only
"""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.career import (
    ApplicationEvent,
    Interview,
    JobApplication,
    Offer,
    Opportunity,
    WorkDnaProfile,
)


# --- Work DNA ----------------------------------------------------------------

def test_work_dna_questions_and_submit(client, make_user):
    user = make_user("dna@example.com")
    questions = client.get(
        "/api/v1/jobseeker/work-dna/questions", headers=user["authorization"]
    )
    assert questions.status_code == 200
    body = questions.json()
    assert len(body) == 8
    keys = {q["key"] for q in body}

    # Incomplete answers rejected.
    bad = client.post(
        "/api/v1/jobseeker/work-dna/assessments",
        headers=user["authorization"],
        json={"answers": {"problem_solving": "analyze"}},
    )
    assert bad.status_code == 422

    answers = {q["key"]: q["options"][0]["value"] for q in body}
    response = client.post(
        "/api/v1/jobseeker/work-dna/assessments",
        headers=user["authorization"],
        json={"answers": answers},
    )
    assert response.status_code == 201, response.text
    profile = response.json()
    assert profile["version"] == "v1"
    assert len(profile["dimensions"]) >= 1
    for dim in profile["dimensions"]:
        assert "key" in dim and "label" in dim and "signal" in dim and "confidence" in dim

    # Latest profile retrievable.
    mine = client.get("/api/v1/jobseeker/work-dna", headers=user["authorization"])
    assert mine.status_code == 200
    assert mine.json()["id"] == profile["id"]


def test_work_dna_invalid_answers_rejected(client, make_user):
    user = make_user("dna2@example.com")
    response = client.post(
        "/api/v1/jobseeker/work-dna/assessments",
        headers=user["authorization"],
        json={"answers": {"problem_solving": "not_an_option", "work_style": "solo_deep"}},
    )
    assert response.status_code == 422  # InvalidInputError envelope


def test_work_dna_ownership_isolated(client, make_user, db):
    alice = make_user("dna_a@example.com")
    bob = make_user("dna_b@example.com")
    questions = client.get(
        "/api/v1/jobseeker/work-dna/questions", headers=alice["authorization"]
    ).json()
    answers = {q["key"]: q["options"][0]["value"] for q in questions}
    created = client.post(
        "/api/v1/jobseeker/work-dna/assessments",
        headers=alice["authorization"],
        json={"answers": answers},
    )
    assert created.status_code == 201
    alice_dna_id = created.json()["id"]

    # Bob sees his own (empty) profile, never Alice's record.
    bob_view = client.get("/api/v1/jobseeker/work-dna", headers=bob["authorization"])
    assert bob_view.status_code == 200
    assert bob_view.json() is None

    stored = db.get(WorkDnaProfile, uuid.UUID(alice_dna_id))
    assert stored.person_id is not None


# --- Opportunities + explainable matching ------------------------------------

def _profile_skill_fixture(client, user, skills):
    for skill in skills:
        response = client.put(
            "/api/v1/work-id/skills",
            headers=user["authorization"],
            json={"skill_name": skill, "level": "advanced", "years_experience": 5},
        )
        assert response.status_code == 200, response.text


def test_opportunity_listing_with_explainable_match(client, make_user, make_opportunity, db):
    user = make_user("opp@example.com")
    make_opportunity(
        company_name="Dot Protocol",
        title="Senior Blockchain Engineer",
        skills_required=["python", "rust", "distributed systems"],
        industry="Blockchain",
    )
    _profile_skill_fixture(client, user, ["Python", "Rust"])

    response = client.get(
        "/api/v1/jobseeker/opportunities", headers=user["authorization"]
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert "components" in item
    assert item["components"]["skills"]["matched"] == ["python", "rust"]
    assert "distributed systems" in item["components"]["skills"]["missing"]
    assert item["missing_skills"] == ["distributed systems"]
    assert item["strengths"] and item["gaps"]  # explainability, never a bare %
    assert item["saved"] is False and item["applied"] is False


def test_opportunity_save_dismiss_apply(client, make_user, make_opportunity):
    user = make_user("opp2@example.com")
    opp = make_opportunity(title="Full-Stack Engineer", skills_required=["python"])
    _profile_skill_fixture(client, user, ["Python"])

    # Save
    saved = client.post(
        f"/api/v1/jobseeker/opportunities/{opp.id}/save",
        headers=user["authorization"],
    )
    assert saved.status_code == 200
    assert saved.json()["status"] == "saved"
    saved_app_id = saved.json()["id"]

    # Apply from saved
    applied = client.post(
        "/api/v1/jobseeker/applications",
        headers=user["authorization"],
        json={"opportunity_id": str(opp.id), "cover_note": "I am a great fit."},
    )
    assert applied.status_code == 201, applied.text
    assert applied.json()["status"] == "applied"
    assert applied.json()["applied_at"] is not None

    # Duplicate apply rejected by state machine (can't re-apply from applied).
    dup = client.post(
        "/api/v1/jobseeker/applications",
        headers=user["authorization"],
        json={"opportunity_id": str(opp.id)},
    )
    assert dup.status_code == 422

    # Timeline exists with at least two events (saved implicit -> applied).
    detail = client.get(
        f"/api/v1/jobseeker/applications/{applied.json()['id']}",
        headers=user["authorization"],
    )
    assert detail.status_code == 200
    assert len(detail.json()["timeline"]) >= 1
    assert detail.json()["timeline"][-1]["to_status"] == "applied"

    # Dismiss a different opportunity.
    opp2 = make_opportunity(title="Brand Designer", skills_required=["figma"])
    dismissed = client.post(
        f"/api/v1/jobseeker/opportunities/{opp2.id}/dismiss",
        headers=user["authorization"],
    )
    assert dismissed.status_code == 200


def test_apply_requires_minimum_work_id(client, make_user, make_opportunity):
    """Empty-profile spam is blocked — the marketplace stays honest."""
    user = make_user("empty@example.com")
    opp = make_opportunity(title="Engineer")
    response = client.post(
        "/api/v1/jobseeker/applications",
        headers=user["authorization"],
        json={"opportunity_id": str(opp.id)},
    )
    assert response.status_code == 422
    assert "skill" in response.json()["error"]["message"].lower()


def test_application_withdraw_lifecycle(client, make_user, make_opportunity):
    user = make_user("withdraw@example.com")
    opp = make_opportunity(title="Platform Engineer", skills_required=["python"])
    _profile_skill_fixture(client, user, ["Python"])
    applied = client.post(
        "/api/v1/jobseeker/applications",
        headers=user["authorization"],
        json={"opportunity_id": str(opp.id)},
    ).json()

    withdrawn = client.post(
        f"/api/v1/jobseeker/applications/{applied['id']}/withdraw",
        headers=user["authorization"],
        params={"reason": "Accepted another role"},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"

    # Cannot withdraw again from a terminal state.
    again = client.post(
        f"/api/v1/jobseeker/applications/{applied['id']}/withdraw",
        headers=user["authorization"],
    )
    assert again.status_code == 422


def test_application_ownership_isolation(client, make_user, make_opportunity):
    """PHASE-5 REGRESSION: A cannot see/modify/withdraw B's application."""
    alice = make_user("app_a@example.com")
    bob = make_user("app_b@example.com")
    opp = make_opportunity(title="Backend Engineer", skills_required=["python"])
    _profile_skill_fixture(client, alice, ["Python"])
    _profile_skill_fixture(client, bob, ["Python"])

    alice_app = client.post(
        "/api/v1/jobseeker/applications",
        headers=alice["authorization"],
        json={"opportunity_id": str(opp.id)},
    ).json()

    # Bob cannot read or withdraw Alice's application.
    bob_read = client.get(
        f"/api/v1/jobseeker/applications/{alice_app['id']}",
        headers=bob["authorization"],
    )
    assert bob_read.status_code == 404
    bob_withdraw = client.post(
        f"/api/v1/jobseeker/applications/{alice_app['id']}/withdraw",
        headers=bob["authorization"],
    )
    assert bob_withdraw.status_code == 404

    # Bob's application list never contains Alice's application.
    bob_list = client.get(
        "/api/v1/jobseeker/applications", headers=bob["authorization"]
    ).json()
    assert all(a["id"] != alice_app["id"] for a in bob_list)


def test_cross_user_goals_milestones(client, make_user):
    alice = make_user("goal_a@example.com")
    bob = make_user("goal_b@example.com")
    goal = client.post(
        "/api/v1/jobseeker/goals",
        headers=alice["authorization"],
        json={
            "title": "Become a Staff Engineer",
            "target_role": "Staff Engineer",
            "target_industries": ["Software"],
            "preferred_work_modes": ["remote", "hybrid"],
        },
    ).json()

    bob_update = client.patch(
        f"/api/v1/jobseeker/goals/{goal['id']}",
        headers=bob["authorization"],
        json={"target_role": "Hijacked"},
    )
    assert bob_update.status_code == 404
    bob_delete = client.delete(
        f"/api/v1/jobseeker/goals/{goal['id']}", headers=bob["authorization"]
    )
    assert bob_delete.status_code == 404

    milestone = client.post(
        "/api/v1/jobseeker/milestones",
        headers=alice["authorization"],
        json={
            "kind": "promotion",
            "title": "Promoted to Senior",
            "occurred_on": "2024-06-01",
        },
    ).json()
    bob_milestone = client.delete(
        f"/api/v1/jobseeker/milestones/{milestone['id']}",
        headers=bob["authorization"],
    )
    assert bob_milestone.status_code == 404


# --- Interviews / offers -----------------------------------------------------

def _setup_interview_flow(client, make_user, make_opportunity, db, email):
    user = make_user(email)
    opp = make_opportunity(title="Data Engineer", skills_required=["python", "sql"])
    _profile_skill_fixture(client, user, ["Python", "SQL"])
    app = client.post(
        "/api/v1/jobseeker/applications",
        headers=user["authorization"],
        json={"opportunity_id": str(opp.id)},
    ).json()

    from datetime import datetime, timedelta

    # An employer-side event (simulated server-side for the candidate center).
    db_app = db.get(JobApplication, uuid.UUID(app["id"]))
    db.add(
        Interview(
            application_id=db_app.id,
            scheduled_at=datetime.utcnow() + timedelta(days=2),
            duration_minutes=45,
            mode="video",
            status="scheduled",
            interviewer_name="Hiring Manager",
        )
    )
    db.commit()
    return user, app


def test_interview_center_and_reschedule_policy(client, make_user, make_opportunity, db):
    user, app = _setup_interview_flow(
        client, make_user, make_opportunity, db, "iv@example.com"
    )

    interviews = client.get(
        "/api/v1/jobseeker/interviews", headers=user["authorization"], params={"upcoming": True}
    )
    assert interviews.status_code == 200
    assert len(interviews.json()) == 1
    interview_id = interviews.json()[0]["id"]

    # Valid reschedule request.
    reschedule = client.post(
        f"/api/v1/jobseeker/interviews/{interview_id}/reschedule-request",
        headers=user["authorization"],
        json={"reason": "Client demo conflict — can we move to Thursday?"},
    )
    assert reschedule.status_code == 200
    assert reschedule.json()["status"] == "reschedule_requested"
    assert reschedule.json()["reschedule_count"] == 0

    # Reschedule without a reason is rejected.
    no_reason = client.post(
        f"/api/v1/jobseeker/interviews/{interview_id}/reschedule-request",
        headers=user["authorization"],
        json={"reason": "x"},
    )
    assert no_reason.status_code == 422


def test_interview_reschedule_limit_enforced(client, make_user, make_opportunity, db):
    user, app = _setup_interview_flow(
        client, make_user, make_opportunity, db, "iv_limit@example.com"
    )
    interview = db.scalar(select(Interview).where(Interview.application_id == uuid.UUID(app["id"])))
    interview.reschedule_count = 2  # at the configured limit (default 2)
    db.commit()

    response = client.post(
        f"/api/v1/jobseeker/interviews/{interview.id}/reschedule-request",
        headers=user["authorization"],
        json={"reason": "Another conflict came up."},
    )
    assert response.status_code == 422
    assert "limit" in response.json()["error"]["message"].lower()


def test_interview_and_offer_ownership(client, make_user, make_opportunity, db):
    user, app = _setup_interview_flow(
        client, make_user, make_opportunity, db, "iv_own@example.com"
    )
    interview_id = client.get(
        "/api/v1/jobseeker/interviews", headers=user["authorization"]
    ).json()[0]["id"]

    other = make_user("iv_other@example.com")
    # Other user cannot see or reschedule this interview.
    other_view = client.get(
        "/api/v1/jobseeker/interviews", headers=other["authorization"]
    ).json()
    assert all(i["id"] != interview_id for i in other_view)
    other_reschedule = client.post(
        f"/api/v1/jobseeker/interviews/{interview_id}/reschedule-request",
        headers=other["authorization"],
        json={"reason": "I would like to reschedule your interview."},
    )
    assert other_reschedule.status_code == 404

    # Offer attached to this application; only the owner can decide it.
    offer = Offer(
        application_id=uuid.UUID(app["id"]),
        status="pending",
        salary_amount=150000,
        salary_currency="USD",
        start_date=__import__("datetime").date(2026, 1, 1),
    )
    db.add(offer)
    db.commit()

    other_decision = client.post(
        f"/api/v1/jobseeker/offers/{offer.id}/decision",
        headers=other["authorization"],
        json={"decision": "accepted"},
    )
    assert other_decision.status_code == 404

    # Owner declines.
    decision = client.post(
        f"/api/v1/jobseeker/offers/{offer.id}/decision",
        headers=user["authorization"],
        json={"decision": "declined"},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "declined"

    # Cannot respond twice.
    again = client.post(
        f"/api/v1/jobseeker/offers/{offer.id}/decision",
        headers=user["authorization"],
        json={"decision": "accepted"},
    )
    assert again.status_code == 422


def test_offer_acceptance_moves_application(client, make_user, make_opportunity, db):
    user, app = _setup_interview_flow(
        client, make_user, make_opportunity, db, "offer_accept@example.com"
    )
    offer = Offer(
        application_id=uuid.UUID(app["id"]),
        status="pending",
        salary_amount=120000,
        salary_currency="USD",
    )
    db.add(offer)
    db.commit()

    accepted = client.post(
        f"/api/v1/jobseeker/offers/{offer.id}/decision",
        headers=user["authorization"],
        json={"decision": "accepted"},
    )
    assert accepted.status_code == 200

    app_detail = client.get(
        f"/api/v1/jobseeker/applications/{app['id']}", headers=user["authorization"]
    ).json()
    assert app_detail["application"]["status"] == "accepted"
    assert app_detail["timeline"][-1]["to_status"] == "accepted"


# --- Dashboard + advisor -----------------------------------------------------

def test_dashboard_aggregates_owned_data(client, make_user, make_opportunity):
    user = make_user("dash@example.com")
    opp = make_opportunity(title="AI Engineer", skills_required=["python", "pytorch"])
    _profile_skill_fixture(client, user, ["Python"])

    dash = client.get("/api/v1/jobseeker/dashboard", headers=user["authorization"])
    assert dash.status_code == 200
    body = dash.json()
    assert body["profile_completion"] is not None
    assert body["work_dna_status"] == "incomplete"
    assert body["has_career_goal"] is False
    assert body["stats"]["applications"] == 0
    assert "recommended" in body
    assert body["advisor"]["disclaimer"]

    # Set a goal and complete Work DNA -> dashboard reflects it.
    client.post(
        "/api/v1/jobseeker/goals",
        headers=user["authorization"],
        json={"title": "AI Engineer", "target_role": "AI Engineer"},
    )
    questions = client.get(
        "/api/v1/jobseeker/work-dna/questions", headers=user["authorization"]
    ).json()
    answers = {q["key"]: q["options"][0]["value"] for q in questions}
    client.post(
        "/api/v1/jobseeker/work-dna/assessments",
        headers=user["authorization"],
        json={"answers": answers},
    )
    dash2 = client.get("/api/v1/jobseeker/dashboard", headers=user["authorization"]).json()
    assert dash2["work_dna_status"] == "completed"
    assert dash2["has_career_goal"] is True
    assert dash2["advisor"]["career_goal"]["target_role"] == "AI Engineer"


def test_advisor_snapshot_no_invention(client, make_user):
    """Advisor with an empty Work ID must not fabricate a career position."""
    user = make_user("adv@example.com")
    snapshot = client.get("/api/v1/jobseeker/advisor", headers=user["authorization"])
    assert snapshot.status_code == 200
    body = snapshot.json()
    assert body["current_position"]["title"] is None
    assert body["roles_held"] == []
    assert body["next_actions"]  # concrete first actions, not invented claims
    # The disclaimer explicitly says outcomes are not guaranteed (honesty rule).
    assert "no career outcome is guaranteed" in body["disclaimer"].lower()


def test_opportunity_route_notifications(client, make_user, make_opportunity):
    user = make_user("notify@example.com")
    opp = make_opportunity(title="DevOps Engineer", skills_required=["aws"])
    _profile_skill_fixture(client, user, ["AWS"])
    client.post(
        "/api/v1/jobseeker/applications",
        headers=user["authorization"],
        json={"opportunity_id": str(opp.id)},
    )

    feed = client.get("/api/v1/jobseeker/notifications", headers=user["authorization"])
    assert feed.status_code == 200
    assert any(n["kind"] == "application" for n in feed.json())

    unread = client.get(
        "/api/v1/jobseeker/notifications/unread-count", headers=user["authorization"]
    ).json()
    assert unread["unread"] >= 1

    first_id = feed.json()[0]["id"]
    marked = client.post(
        f"/api/v1/jobseeker/notifications/{first_id}/read",
        headers=user["authorization"],
    )
    assert marked.status_code == 200

    # Other users cannot read our notifications.
    other = make_user("notify_other@example.com")
    other_feed = client.get(
        "/api/v1/jobseeker/notifications", headers=other["authorization"]
    ).json()
    assert all(n["id"] != first_id for n in other_feed)
