"""Phase 15 — Career Advisor + AI interview preparation tests.

Deterministic evaluation (no live LLM): the structured facts are
validated independently of any model, and Athena integration uses the
scripted FakeProvider from the Phase 14 harness. Coverage:

- career profile digest accuracy + sensitive-data exclusion
- deterministic skill-gap analysis (matched / partial / missing)
- career-path anchoring and classification
- opportunity recommendations modes + career signals
- application analysis (funnel, movement, stuck)
- action plan (suggestion-only, no side effects)
- interview-prep sessions (owner isolation, lazy expiry, deletion,
  retention: answers are never persisted)
- question generation + answer evaluation determinism
- Athena tool integration incl. bulk-apply exact-scope confirmations
- adversarial: cross-user isolation, fabrication refused, employer vs
  jobseeker tool boundaries
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athena import AthenaActionConfirmation, AthenaMessage, AthenaSession
from app.models.audit import AuditLogEntry
from app.models.career import JobApplication, Opportunity
from app.models.identity import PersonProfile, User
from app.models.interview_prep import InterviewPrepSession
from app.models.talent import CareerPath, CareerPathStep
from app.models.tenancy import Membership, Organization
from app.models.work import Credential, WorkExperience

from tests_phase3.test_athena_phase14 import (  # noqa: F401  (reuse fakes/helpers)
    FakeProvider,
    _create_session,
    _monkeypatch_provider,
    _plain,
    _tool,
)


# --- helpers ------------------------------------------------------------------

def _user_id(db: Session, email: str) -> uuid.UUID:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None, email
    return user.id


def _person_id(db: Session, email: str) -> uuid.UUID:
    uid = _user_id(db, email)
    person = db.scalar(select(PersonProfile).where(PersonProfile.user_id == uid))
    assert person is not None
    return person.id


def _add_profile(client, user, **kwargs):
    body = {"headline": "Platform Engineer", "city": "Dubai", "country_code": "AE"}
    body.update(kwargs)
    r = client.put("/api/v1/work-id/profile", headers=user["authorization"], json=body)
    assert r.status_code == 200, r.text


def _add_experience(client, user, title="Platform Engineer", company="Acme Corp",
                    start="2020-01-01", current=True):
    r = client.post(
        "/api/v1/work-id/experiences",
        headers=user["authorization"],
        json={
            "company_name": company,
            "title": title,
            "start_date": start,
            "is_current": current,
        },
    )
    assert r.status_code == 201, r.text


def _add_skills(client, user, *skills):
    for skill in skills:
        r = client.put(
            "/api/v1/work-id/skills",
            headers=user["authorization"],
            json={"skill_name": skill, "level": "advanced", "years_experience": 4},
        )
        assert r.status_code == 200, r.text


def _add_credential(db, person_id, name="PMP", issuer="PMI", status="unverified"):
    db.add(
        Credential(person_id=person_id, name=name, issuer=issuer, status=status)
    )
    db.commit()


def _add_goal(client, user, title="Move to data", target_role="Data Engineer"):
    r = client.post(
        "/api/v1/jobseeker/goals",
        headers=user["authorization"],
        json={
            "title": title,
            "target_role": target_role,
            "target_industries": ["Technology"],
            "is_primary": True,
        },
    )
    assert r.status_code == 201, r.text


def _seed_opportunity(db, *, title="Data Engineer", skills=None, company="Acme"):
    """Insert one opportunity; returns its UUID (safe outside the session)."""
    opp = Opportunity(
        id=uuid.uuid4(),
        company_name=company,
        title=title,
        summary=f"{title} at {company}",
        skills_required=skills or ["Python", "SQL"],
        status="active",
        is_approved=True,
        experience_level="3+ years",
        seniority="mid",
        industry="Technology",
    )
    db.add(opp)
    db.flush()
    opp_id = opp.id
    db.commit()
    return opp_id


def _seed_path(db, *, title="Data Engineering track", target="Data Engineer",
               steps=("Data Analyst", "Data Engineer")):
    path = CareerPath(title=title, target_role=target, status="active")
    db.add(path)
    db.flush()
    for order, role in enumerate(steps, start=1):
        db.add(
            CareerPathStep(
                path_id=path.id, step_order=order, role_title=role,
                skills_required=["SQL", "Python"][: order],
            )
        )
    db.commit()
    return path


# --- Career profile digest ----------------------------------------------------

def test_digest_accuracy_and_minimization(client, make_user, db):
    user = make_user(f"d{uuid.uuid4().hex[:6]}@example.com")
    _add_profile(client, user)
    _add_experience(client, user)
    _add_skills(client, user, "Python", "SQL")
    pid = _person_id(db, user["email"])
    _add_credential(db, pid, name="PMP", status="unverified")
    # Sensitive fields are set on the profile row to prove they never leak.
    with Session(db.bind) as s:
        person = s.get(PersonProfile, pid)
        person.phone = "+27 000 000 0000"
        person.date_of_birth = datetime(1990, 1, 1, tzinfo=timezone.utc)
        s.commit()

    digest = client.get(
        "/api/v1/career-advisor/digest", headers=user["authorization"]
    ).json()
    assert digest["current_position"]["title"] == "Platform Engineer"
    assert digest["experience_summary"]["roles_held"] == 1
    assert digest["credentials"]["verified"] == []
    assert len(digest["credentials"]["unverified"]) == 1
    assert digest["credentials"]["unverified"][0]["name"] == "PMP"
    assert digest["credentials"]["note"]  # honesty note present
    assert {"name": "python"} in digest["skills"]["all"] or any(
        s["name"] == "python" for s in digest["skills"]["all"]
    )
    raw = json.dumps(digest).lower()
    assert "+27" not in raw
    assert "1990" not in raw
    assert "phone" not in raw and "date_of_birth" not in raw


def test_digest_cross_user_isolation(client, make_user):
    a = make_user(f"da{uuid.uuid4().hex[:6]}@example.com")
    b = make_user(f"db{uuid.uuid4().hex[:6]}@example.com")
    _add_profile(client, a, headline="Alpha Engineer")
    _add_profile(client, b, headline="Beta Analyst")
    da = client.get("/api/v1/career-advisor/digest", headers=a["authorization"]).json()
    db_ = client.get("/api/v1/career-advisor/digest", headers=b["authorization"]).json()
    assert "Alpha" in da["professional_summary"]
    assert "Beta" in db_["professional_summary"]
    assert "Beta" not in da["professional_summary"]
    assert "Alpha" not in db_["professional_summary"]


def test_career_endpoints_require_auth(client):
    assert client.get("/api/v1/career-advisor/digest").status_code == 401
    assert client.get("/api/v1/career-advisor/gaps").status_code == 401
    assert client.get("/api/v1/career-advisor/applications").status_code == 401


# --- Skill-gap analysis -------------------------------------------------------

def test_gap_analysis_matched_partial_missing(client, make_user, db):
    """Role requires Rust; candidate lacks Rust but holds Go (taxonomy says
    Rust ~ related ~ Go): Rust must come back PARTIAL, not missing."""
    from app.models.talent import SkillRelationship
    from app.models.work import Skill

    user = make_user(f"g{uuid.uuid4().hex[:6]}@example.com")
    with Session(db.bind) as s:
        for name in ("Go", "Rust"):
            existing = s.scalar(select(Skill).where(Skill.name.ilike(name)))
            if existing is None:
                s.add(Skill(name=name, category="general"))
        s.flush()
        go = s.scalar(select(Skill).where(Skill.name.ilike("go")))
        rust = s.scalar(select(Skill).where(Skill.name.ilike("rust")))
        if not s.scalar(
            select(SkillRelationship).where(
                SkillRelationship.skill_id == rust.id,
                SkillRelationship.related_skill_id == go.id,
            )
        ):
            s.add(
                SkillRelationship(
                    skill_id=rust.id, related_skill_id=go.id, kind="related"
                )
            )
        s.commit()
    _add_skills(client, user, "Python", "SQL", "Go")
    with Session(db.bind) as s:
        opp_id = _seed_opportunity(s, skills=["Python", "Rust", "Kubernetes"])

    resp = client.get(
        f"/api/v1/career-advisor/gaps?opportunity_id={opp_id}",
        headers=user["authorization"],
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["target_kind"] == "opportunity"
    matched = {m["skill"].lower() for m in body["matched_skills"]}
    partial = {p["skill"].lower() for p in body["partial_skills"]}
    missing = {m["skill"].lower() for m in body["missing_skills"]}
    assert matched == {"python"}
    assert "rust" in partial  # related skill only (candidate has Go)
    assert missing == {"kubernetes"}
    assert body["skill_coverage"] == pytest.approx(1 / 3, abs=0.001)
    assert body["experience_gap"] is not None  # no experience recorded, 3+ needed


def test_gap_analysis_unknown_opportunity(client, make_user):
    user = make_user(f"gu{uuid.uuid4().hex[:6]}@example.com")
    resp = client.get(
        f"/api/v1/career-advisor/gaps?opportunity_id={uuid.uuid4()}",
        headers=user["authorization"],
    )
    assert resp.status_code == 404


# --- Career paths -------------------------------------------------------------

def test_career_paths_direct_and_transition(client, make_user, db):
    user = make_user(f"p{uuid.uuid4().hex[:6]}@example.com")
    _add_experience(client, user, title="Data Analyst", company="Small Co")
    _seed_path(db)
    body = client.get(
        "/api/v1/career-advisor/paths", headers=user["authorization"]
    ).json()
    assert body["anchor"] == "Data Analyst"
    assert body["paths"]
    direct = next(x for x in body["paths"] if x["classification"] == "direct")
    assert direct["current_step"] == "Data Analyst"
    assert direct["next_step"]["role_title"] == "Data Engineer"
    assert direct["gap_to_next_step"]["to_role"] == "Data Engineer"

    # Transition: a person with unrelated history whose GOAL is Data Engineer.
    user2 = make_user(f"p2{uuid.uuid4().hex[:6]}@example.com")
    _add_experience(client, user2, title="Cashier", company="Shop")
    _add_goal(client, user2, target_role="Data Engineer")
    body2 = client.get(
        "/api/v1/career-advisor/paths", headers=user2["authorization"]
    ).json()
    assert body2["paths"]
    assert any(x["classification"] == "transition" for x in body2["paths"])


# --- Opportunity recommendations ----------------------------------------------

def test_recommendation_modes(client, make_user, db):
    user = make_user(f"r{uuid.uuid4().hex[:6]}@example.com")
    _add_experience(client, user, start="2016-01-01")  # 8+ years
    _add_skills(client, user, "Python", "SQL", "Kubernetes", "AWS")
    with Session(db.bind) as s:
        strong_opp = str(
            _seed_opportunity(s, title="Data Engineer", skills=["Python", "SQL"])
        )
        weak_opp = str(
            _seed_opportunity(s, title="Robotics Lead", skills=["C++", "ROS"])
        )

    strong = client.get(
        "/api/v1/career-advisor/opportunities?mode=strong",
        headers=user["authorization"],
    ).json()
    assert strong["mode"] == "strong"
    ids = {i["opportunity_id"] for i in strong["items"]}
    assert strong_opp in ids
    assert weak_opp not in ids
    item = next(i for i in strong["items"] if i["opportunity_id"] == strong_opp)
    assert item["percent"] >= 80
    assert item["missing_skills"] == []
    assert item["strengths"]

    explore = client.get(
        "/api/v1/career-advisor/opportunities?mode=explore",
        headers=user["authorization"],
    ).json()
    assert explore["count"] == 2

    bad = client.get(
        "/api/v1/career-advisor/opportunities?mode=bogus",
        headers=user["authorization"],
    )
    assert bad.status_code == 422


# --- Application analysis -----------------------------------------------------

def test_application_analysis(client, make_user, db):
    user = make_user(f"a{uuid.uuid4().hex[:6]}@example.com")
    pid = _person_id(db, user["email"])
    with Session(db.bind) as s:
        opp_rejected = _seed_opportunity(s, title="Rejected Role", company="CoA")
        opp_stuck = _seed_opportunity(s, title="Stuck Role", company="CoB")
        opp_interview = _seed_opportunity(s, title="Interview Role", company="CoC")
        s.add(
            JobApplication(
                person_id=pid, opportunity_id=opp_rejected,
                status="rejected",
                applied_at=datetime.now(timezone.utc) - timedelta(days=30),
            )
        )
        s.add(
            JobApplication(
                person_id=pid, opportunity_id=opp_stuck,
                status="applied",
                applied_at=datetime.now(timezone.utc) - timedelta(days=30),
            )
        )
        s.add(
            JobApplication(
                person_id=pid, opportunity_id=opp_interview,
                status="interview",
                applied_at=datetime.now(timezone.utc) - timedelta(days=10),
            )
        )
        s.commit()

    body = client.get(
        "/api/v1/career-advisor/applications", headers=user["authorization"]
    ).json()
    assert body["application_count"] == 3
    assert body["applied_count"] == 3
    assert body["advanced_count"] == 1
    assert body["movement_rate"] == pytest.approx(1 / 3, abs=0.01)
    assert body["status_counts"]["rejected"] == 1
    assert body["status_counts"]["interview"] == 1
    assert len(body["stuck_applications"]) == 1  # the 30-day-old "applied" one
    assert body["stuck_applications"][0]["days"] >= 21
    assert body["advice"]


def test_action_plan_is_suggestion_only(client, make_user, db):
    user = make_user(f"ap{uuid.uuid4().hex[:6]}@example.com")
    _add_skills(client, user, "Python")
    _add_goal(client, user, target_role="Data Engineer")
    body = client.get(
        "/api/v1/career-advisor/action-plan", headers=user["authorization"]
    ).json()
    assert body["goal"]["target_role"] == "Data Engineer"
    assert body["actions"]
    assert all("target_week" in a for a in body["actions"])
    assert body["milestone_suggestions"]
    assert all(m["suggested"] is True for m in body["milestone_suggestions"])
    # No side effects: no milestone rows were created by a GET.
    with Session(db.bind) as s:
        from app.models.career import CareerMilestone
        assert s.scalar(select(CareerMilestone)) is None


# --- Interview preparation ----------------------------------------------------

def _prep_session(client, user, db, opp=None, **kw):
    """opp is a UUID (string or UUID object) of a seeded opportunity."""
    body = kw
    if opp is not None:
        body["opportunity_id"] = str(opp)
    r = client.post("/api/v1/interview-prep/sessions", headers=user["authorization"], json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_prep_session_lifecycle_and_isolation(client, make_user, db):
    a = make_user(f"i{uuid.uuid4().hex[:6]}@example.com")
    b = make_user(f"j{uuid.uuid4().hex[:6]}@example.com")
    with Session(db.bind) as s:
        opp_id = _seed_opportunity(s, skills=["Python", "SQL"])

    created = _prep_session(client, a, db, opp=opp_id, focus_areas=["Python", "SQL"])
    sid = created["id"]
    assert created["status"] == "active"
    assert created["opportunity_id"] == str(opp_id)

    # Owner sees it; the other user cannot.
    mine = client.get("/api/v1/interview-prep/sessions", headers=a["authorization"]).json()
    assert [x["id"] for x in mine] == [sid]
    theirs = client.get("/api/v1/interview-prep/sessions", headers=b["authorization"]).json()
    assert theirs == []
    assert (
        client.get(f"/api/v1/interview-prep/sessions/{sid}", headers=b["authorization"]).status_code
        == 404
    )
    # An anchored opportunity must exist.
    ghost = client.post(
        "/api/v1/interview-prep/sessions",
        headers=a["authorization"],
        json={"opportunity_id": str(uuid.uuid4())},
    )
    assert ghost.status_code == 404

    # Questions + answers keep the session active; complete; then delete.
    qr = client.post(
        f"/api/v1/interview-prep/sessions/{sid}/questions",
        headers=a["authorization"],
        json={"count": 4},
    )
    assert qr.status_code == 200, qr.text
    qs = qr.json()
    assert qs["count"] == 4
    categories = {q["category"] for q in qs["questions"]}
    assert categories <= {
        "behavioral", "technical", "role_specific", "competency",
        "situational", "career_history",
    }
    technical = next((q for q in qs["questions"] if q["category"] == "technical"), None)
    assert technical is not None, "anchored technical question expected"
    assert "Python" in technical["question"] or "SQL" in technical["question"]

    answer = (
        "Situation: our platform onboarding took too long. Task: I owned the "
        "revamp. Action: I built an automated checklist in Python and SQL "
        "dashboards to track it. Result: time to value dropped 30%."
    )
    ev = client.post(
        f"/api/v1/interview-prep/sessions/{sid}/answers",
        headers=a["authorization"],
        json={"question": technical["question"], "answer": answer},
    )
    assert ev.status_code == 200, ev.text
    dims = ev.json()["dimensions"]
    assert set(dims) == {
        "relevance", "structure", "evidence", "role_knowledge",
        "communication", "completeness",
    }
    assert all(0 <= d["score"] <= 1 for d in dims.values())
    assert dims["evidence"]["score"] >= 0.9
    assert ev.json()["disclaimer"]
    # The evaluation is deterministic: re-evaluate identical input -> identical.
    ev2 = client.post(
        f"/api/v1/interview-prep/sessions/{sid}/answers",
        headers=a["authorization"],
        json={"question": technical["question"], "answer": answer},
    ).json()
    assert ev2["dimensions"] == dims

    complete = client.post(
        f"/api/v1/interview-prep/sessions/{sid}/complete",
        headers=a["authorization"],
    ).json()
    assert complete["status"] == "completed"
    assert client.post(
        f"/api/v1/interview-prep/sessions/{sid}/questions",
        headers=a["authorization"],
        json={"count": 2},
    ).status_code == 422  # completed session refuses new questions

    assert (
        client.delete(
            f"/api/v1/interview-prep/sessions/{sid}", headers=b["authorization"]
        ).status_code
        == 404
    )
    dele = client.delete(
        f"/api/v1/interview-prep/sessions/{sid}", headers=a["authorization"]
    )
    assert dele.status_code == 204
    with Session(db.bind) as s:
        assert s.get(InterviewPrepSession, uuid.UUID(sid)) is None


def test_prep_answers_never_persisted(client, make_user, db):
    """Retention contract: mock answers are NOT stored anywhere."""
    user = make_user(f"k{uuid.uuid4().hex[:6]}@example.com")
    with Session(db.bind) as s:
        opp_id = _seed_opportunity(s, skills=["Python"])
    created = _prep_session(client, user, db, opp=opp_id)
    sid = created["id"]
    q = client.post(
        f"/api/v1/interview-prep/sessions/{sid}/questions",
        headers=user["authorization"],
        json={"count": 1},
    ).json()["questions"][0]
    secret = "unique-mock-answer-xyz-4242"
    ev = client.post(
        f"/api/v1/interview-prep/sessions/{sid}/answers",
        headers=user["authorization"],
        json={"question": q["question"], "answer": secret},
    )
    assert ev.status_code == 200
    with Session(db.bind) as s:
        # No table stores the answer: search every JSON/text-ish column
        # surface that could carry it via raw SQL across all tables.
        from sqlalchemy import text
        tables = s.execute(
            text("select name from sqlite_master where type='table'")
        ).scalars().all()
        leaked = []
        for table in tables:
            cols = [r[0] for r in s.execute(text(f"PRAGMA table_info('{table}')")).all()]
            for col in cols:
                try:
                    rows = s.execute(
                        text(f"select [{col}] from [{table}] where [{col}] like :p"),
                        {"p": f"%{secret}%"},
                    ).all()
                    if rows:
                        leaked.append(f"{table}.{col}")
                except Exception:
                    continue
        assert leaked == [], f"mock answer leaked into: {leaked}"
        # The message table is empty (no Athena chat was used).
        assert s.scalar(select(AthenaMessage)) is None


def test_prep_session_lazy_expiry(client, make_user, db):
    user = make_user(f"l{uuid.uuid4().hex[:6]}@example.com")
    created = _prep_session(client, user, db)
    sid = created["id"]
    with Session(db.bind) as s:
        session = s.get(InterviewPrepSession, uuid.UUID(sid))
        session.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        s.commit()
    # Next touch lazily expires the session without a scheduler.
    assert (
        client.post(
            f"/api/v1/interview-prep/sessions/{sid}/questions",
            headers=user["authorization"],
            json={"count": 1},
        ).status_code
        == 422
    )
    with Session(db.bind) as s:
        assert s.get(InterviewPrepSession, uuid.UUID(sid)).status == "expired"


# --- Athena tool integration (scripted fake provider) -------------------------

def test_athena_career_tools_run_in_jobseeker_mode(client, make_user, monkeypatch, db):
    user = make_user(f"t{uuid.uuid4().hex[:6]}@example.com")
    _add_skills(client, user, "Python")
    _add_goal(client, user, target_role="Data Engineer")
    sid = _create_session(client, user, "jobseeker")
    _monkeypatch_provider(
        monkeypatch,
        FakeProvider([_tool("career.get_action_plan", {})]),
    )
    body = client.post(
        "/api/v1/athena/message",
        headers=user["authorization"],
        json={"session_id": sid, "message": "build my plan"},
    ).json()
    assert body["error"] is None
    assert body["tool_results"], body
    assert body["tool_results"][0]["status"] == "ok"


def test_employer_cannot_reach_career_or_prep_tools(client, make_user, db, monkeypatch):
    emp = make_user(f"m{uuid.uuid4().hex[:6]}@example.com")
    org = Organization(name=f"Org {uuid.uuid4().hex[:6]}", slug=f"o-{uuid.uuid4().hex[:6]}", kind="employer")
    db.add(org)
    db.flush()
    db.add(
        Membership(
            user_id=_user_id(db, emp["email"]),
            organization_id=org.id,
            role_code="org_admin",
            created_by=_user_id(db, emp["email"]),
        )
    )
    db.commit()
    sid = _create_session(client, emp, "employer", org.id)
    for tool in ["career.get_recommendations", "interview.get_prep_session",
                 "career.get_profile_digest"]:
        _monkeypatch_provider(monkeypatch, FakeProvider([_tool(tool, {})]))
        body = client.post(
            "/api/v1/athena/message",
            headers=emp["authorization"],
            json={"session_id": sid, "message": "do it"},
        ).json()
        errors = [r for r in body["tool_results"] if r.get("status") == "error"]
        assert errors, f"{tool} must be refused in employer mode"


def test_fabrication_attempts_have_no_tool(client, make_user, monkeypatch, db):
    """'Invent qualifications' cannot do anything: no such tool exists and
    unregistered names are refused."""
    user = make_user(f"f{uuid.uuid4().hex[:6]}@example.com")
    sid = _create_session(client, user, "jobseeker")
    for bad in ["career.add_certification", "career.fake_experience",
                "interview.invent_score"]:
        _monkeypatch_provider(monkeypatch, FakeProvider([_tool(bad, {})]))
        body = client.post(
            "/api/v1/athena/message",
            headers=user["authorization"],
            json={"session_id": sid, "message": "invent it"},
        ).json()
        denied = [r for r in body["tool_results"] if r.get("status") == "error"]
        assert denied, f"unregistered tool {bad} must be refused"


def _add_org_and_membership(db, email, role="org_admin"):
    from app.models.tenancy import Membership, Organization
    org = Organization(
        name=f"Org {uuid.uuid4().hex[:6]}", slug=f"o-{uuid.uuid4().hex[:6]}",
        kind="employer",
    )
    db.add(org)
    db.flush()
    db.add(
        Membership(
            user_id=_user_id(db, email), organization_id=org.id,
            role_code=role, created_by=_user_id(db, email),
        )
    )
    db.commit()
    return org.id


def test_athena_apply_to_opportunities_exact_scope_confirmation(
    client, make_user, db, monkeypatch
):
    """Bulk apply is confirmation-gated to the EXACT opportunity list.

    Approving for [A] never applies [B]; a changed set needs a new
    confirmation; denial applies nothing.
    """
    from app.models.tenancy import Organization, Membership
    user = make_user(f"ba{uuid.uuid4().hex[:6]}@example.com")
    _add_skills(client, user, "Python")
    with Session(db.bind) as s:
        a_id = _seed_opportunity(s, title="Role A", skills=["Python"])
        b_id = _seed_opportunity(s, title="Role B", skills=["Python"])
    sid = _create_session(client, user, "jobseeker")

    _monkeypatch_provider(
        monkeypatch,
        FakeProvider([_tool("apply_to_opportunities", {"opportunity_ids": [str(a_id)]})]),
    )
    body = client.post(
        "/api/v1/athena/message",
        headers=user["authorization"],
        json={"session_id": sid, "message": "apply to A"},
    ).json()
    assert body["pending_confirmations"], body
    conf_id = body["pending_confirmations"][0]["confirmation_id"]
    # Nothing applied before confirmation.
    with Session(db.bind) as s:
        assert s.scalar(select(JobApplication)) is None
    resp = client.post(
        "/api/v1/athena/confirm",
        headers=user["authorization"],
        json={"confirmation_id": conf_id, "approve": True},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved_and_executed"
    with Session(db.bind) as s:
        apps = s.scalars(select(JobApplication)).all()
        assert len(apps) == 1 and apps[0].opportunity_id == a_id

    # Model now proposes B: the A-confirmation is consumed; new scope => new gate.
    _monkeypatch_provider(
        monkeypatch,
        FakeProvider([_tool("apply_to_opportunities", {"opportunity_ids": [str(b_id)]})]),
    )
    body2 = client.post(
        "/api/v1/athena/message",
        headers=user["authorization"],
        json={"session_id": sid, "message": "apply to B"},
    ).json()
    assert body2["pending_confirmations"], "changed scope must re-require confirmation"
    with Session(db.bind) as s:
        assert not any(a.opportunity_id == b_id for a in s.scalars(select(JobApplication)).all())

    # Deny => nothing new applied.
    conf2 = body2["pending_confirmations"][0]["confirmation_id"]
    deny = client.post(
        "/api/v1/athena/confirm",
        headers=user["authorization"],
        json={"confirmation_id": conf2, "approve": False},
    )
    assert deny.status_code == 200 and deny.json()["status"] == "denied"
    with Session(db.bind) as s:
        apps = s.scalars(select(JobApplication)).all()
        assert len(apps) == 1 and apps[0].opportunity_id == a_id


def test_athena_interview_prep_flow(client, make_user, db, monkeypatch):
    """Mock interview end-to-end through the Athena surface."""
    user = make_user(f"mp{uuid.uuid4().hex[:6]}@example.com")
    _add_skills(client, user, "Python")
    with Session(db.bind) as s:
        opp_id = _seed_opportunity(s, skills=["Python"])
    sid = _create_session(client, user, "jobseeker")

    # Start a prep session via the tool.
    _monkeypatch_provider(
        monkeypatch,
        FakeProvider(
            [_tool("interview.start_prep_session", {"opportunity_id": str(opp_id)})]
        ),
    )
    body = client.post(
        "/api/v1/athena/message",
        headers=user["authorization"],
        json={"session_id": sid, "message": "prepare me for this interview"},
    ).json()
    result = body["tool_results"][0]["result"]
    prep_id = result["id"]
    with Session(db.bind) as s:
        assert s.get(InterviewPrepSession, uuid.UUID(prep_id)) is not None

    # Get questions.
    _monkeypatch_provider(
        monkeypatch,
        FakeProvider([_tool("interview.get_questions", {"session_id": prep_id, "count": 3})]),
    )
    body2 = client.post(
        "/api/v1/athena/message",
        headers=user["authorization"],
        json={"session_id": sid, "message": "ask me questions"},
    ).json()
    qs = body2["tool_results"][0]["result"]["questions"]
    assert len(qs) == 3

    # Submit an answer.
    _monkeypatch_provider(
        monkeypatch,
        FakeProvider(
            [
                _tool(
                    "interview.submit_answer",
                    {
                        "session_id": prep_id,
                        "question": qs[0]["question"],
                        "answer": (
                            "Situation: delivery slipped. Task: recover the plan. "
                            "Action: I re-prioritised with the team in Python tooling. "
                            "Result: we shipped 20% faster."
                        ),
                    },
                )
            ]
        ),
    )
    body3 = client.post(
        "/api/v1/athena/message",
        headers=user["authorization"],
        json={"session_id": sid, "message": "here is my answer"},
    ).json()
    assert body3["tool_results"][0]["status"] == "ok"
    dims = body3["tool_results"][0]["result"]["dimensions"]
    assert "evidence" in dims


def test_prep_audit_contains_no_answer_content(client, make_user, db):
    user = make_user(f"au{uuid.uuid4().hex[:6]}@example.com")
    created = _prep_session(client, user, db)
    sid = created["id"]
    q = client.post(
        f"/api/v1/interview-prep/sessions/{sid}/questions",
        headers=user["authorization"],
        json={"count": 1},
    ).json()["questions"][0]
    secret = "audit-secret-answer-777"
    client.post(
        f"/api/v1/interview-prep/sessions/{sid}/answers",
        headers=user["authorization"],
        json={"question": q["question"], "answer": secret},
    )
    with Session(db.bind) as s:
        payloads = s.scalars(select(AuditLogEntry.payload)).all()
        blob = json.dumps([p or {} for p in payloads])
        assert secret not in blob
        assert "audit-secret" not in blob
        actions = s.scalars(select(AuditLogEntry.action)).all()
        assert any("interview_prep.session.created" in a for a in actions)
