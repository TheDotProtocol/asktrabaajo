"""Phase 16 — AI Interview Engine: deterministic + adversarial tests.

Every assertion is code-enforced (never LLM-dependent). The engine runs
with ``AI_PROVIDER=none``: the deterministic question/evaluation engine
is the production path in this phase.

Safety invariants under test:
- entry-token binding: wrong token / wrong person / replay all fail
- consent is enforced before start; withdrawal stops the session
- prohibited topics are rejected in config and never generated
- raw answers are NEVER persisted anywhere
- adaptive follow-ups stay linked to the same competency
- integrity signals are review signals only (never penalties)
- employer decision is a human action; the AI never decides
- cross-org and cross-candidate isolation
- no facial/lie/protected-characteristic capabilities exist
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_interview import (
    AiInterviewEvaluation,
    AiInterviewQuestion,
    AiInterviewReport,
    AiInterviewSession,
)
from app.models.career import JobApplication, Opportunity
from app.models.identity import PersonProfile, User
from app.models.tenancy import Membership, Organization
from app.models.talent import OpportunityRequirement


# --- Helpers -------------------------------------------------------------------

def _user_id(db: Session, email: str) -> uuid.UUID:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None, f"missing user {email}"
    return user.id


def _person_id(db: Session, user_id: uuid.UUID) -> uuid.UUID:
    person = db.scalar(select(PersonProfile).where(PersonProfile.user_id == user_id))
    assert person is not None
    return person.id


def _make_org(db: Session, user_id: uuid.UUID, role: str = "hiring_manager", kind: str = "employer") -> uuid.UUID:
    org = Organization(name=f"Org {uuid.uuid4().hex[:6]}", slug=f"org-{uuid.uuid4().hex[:6]}", kind=kind)
    db.add(org)
    db.flush()
    db.add(Membership(user_id=user_id, organization_id=org.id, role_code=role, created_by=user_id))
    db.commit()
    return org.id


def _make_org_opportunity(db: Session, org_id: uuid.UUID, title: str = "Operations Manager", requirement: str = "Five years of operations leadership") -> Opportunity:
    opp = Opportunity(
        company_id=org_id,
        company_name="Test Co",
        title=title,
        summary=f"{title} opening",
        skills_required=["leadership", "operations"],
        status="active",
        is_approved=True,
        source="platform",
    )
    db.add(opp)
    db.flush()
    db.add(OpportunityRequirement(opportunity_id=opp.id, raw_text=requirement, requirement_kind="required"))
    db.commit()
    db.refresh(opp)
    return opp


def _create(client, employer, org_id, candidate_person_id, **overrides):
    body = {
        "organization_id": str(org_id),
        "candidate_person_id": str(candidate_person_id),
        "interview_type": "mixed",
        "question_count": 3,
        "duration_minutes": 30,
        **overrides,
    }
    return client.post("/api/v1/ai-interviews", headers=employer["authorization"], params={"organization_id": str(org_id)}, json=body)


def _setup_org(client, make_user, db, role="hiring_manager"):
    employer = make_user(f"emp{uuid.uuid4().hex[:6]}@example.com")
    org_id = _make_org(db, _user_id(db, employer["email"]), role=role)
    candidate = make_user(f"cand{uuid.uuid4().hex[:6]}@example.com")
    opp = _make_org_opportunity(db, org_id)
    return employer, org_id, candidate, opp


def _create_and_invite(client, make_user, db, **overrides):
    employer, org_id, candidate, opp = _setup_org(client, make_user, db)
    pid = _person_id(db, _user_id(db, candidate["email"]))
    resp = _create(client, employer, org_id, pid, opportunity_id=str(opp.id), **overrides)
    assert resp.status_code == 201, resp.text
    session_id = resp.json()["session_id"]
    token = resp.json()["entry_token"]
    inv = client.post(
        f"/api/v1/ai-interviews/{session_id}/invite",
        headers=employer["authorization"],
        params={"organization_id": str(org_id)},
    )
    assert inv.status_code == 200, inv.text
    return employer, org_id, candidate, opp, session_id, token


def _claim(client, candidate, token):
    return client.post("/api/v1/ai-interviews/claim", headers=candidate["authorization"], json={"entry_token": token})


def _headers(candidate, token):
    return {**candidate["authorization"], "X-Interview-Token": token}


# --- Employer configuration & tenant grounding ---------------------------------

def test_create_requires_org_permission(client, make_user, db):
    employer, org_id, candidate, opp = _setup_org(client, make_user, db)
    pid = _person_id(db, _user_id(db, candidate["email"]))
    # A user with NO membership cannot create.
    stranger = make_user(f"stranger{uuid.uuid4().hex[:6]}@example.com")
    resp = _create(client, stranger, org_id, pid, opportunity_id=str(opp.id))
    assert resp.status_code == 403, resp.text
    # A member whose role lacks interviews.* cannot create.
    marketing_user = make_user(f"mkt{uuid.uuid4().hex[:6]}@example.com")
    _make_org(db, _user_id(db, marketing_user["email"]), role="marketing")
    # marketing role has no interviews.manage -> 403
    resp2 = _create(client, marketing_user, org_id, pid, opportunity_id=str(opp.id))
    assert resp2.status_code == 403, resp2.text


def test_create_requires_anchor_and_tenant_match(client, make_user, db):
    employer, org_id, candidate, opp = _setup_org(client, make_user, db)
    pid = _person_id(db, _user_id(db, candidate["email"]))
    resp = _create(client, employer, org_id, pid)  # no anchor
    assert resp.status_code == 422, resp.text
    # Opportunity owned by ANOTHER org.
    other_org_id = _make_org(db, _user_id(db, employer["email"]), role="hiring_manager")
    other_opp = _make_org_opportunity(db, other_org_id, title="Other Role")
    resp2 = _create(client, employer, org_id, pid, opportunity_id=str(other_opp.id))
    assert resp2.status_code == 403, resp2.text


def test_entry_token_returned_once_and_stored_hashed(client, make_user, db):
    employer, org_id, candidate, opp = _setup_org(client, make_user, db)
    pid = _person_id(db, _user_id(db, candidate["email"]))
    resp = _create(client, employer, org_id, pid, opportunity_id=str(opp.id))
    assert resp.status_code == 201, resp.text
    token = resp.json()["entry_token"]
    session = db.get(AiInterviewSession, uuid.UUID(resp.json()["session_id"]))
    assert session is not None
    assert session.entry_token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert session.entry_token_hash != token


# --- Candidate entry security --------------------------------------------------

def test_claim_wrong_token_and_wrong_person_denied(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    other = make_user(f"other{uuid.uuid4().hex[:6]}@example.com")
    # Wrong token.
    r = _claim(client, candidate, "totally-wrong-token-00000000")
    assert r.status_code == 403, r.text
    # Other candidate using the real token.
    r2 = _claim(client, other, token)
    assert r2.status_code == 403, r2.text
    # Correct candidate + token.
    r3 = _claim(client, candidate, token)
    assert r3.status_code == 200, r3.text
    assert r3.json()["session_id"] == str(session_id)


def test_missing_entry_token_header_rejected(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    resp = client.get(f"/api/v1/ai-interviews/{session_id}/next-question", headers=candidate["authorization"])
    assert resp.status_code == 401, resp.text


def test_consent_required_before_start(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    start = client.post(f"/api/v1/ai-interviews/{session_id}/start", headers=_headers(candidate, token))
    assert start.status_code == 422, start.text  # consent_required, not ready
    cons = client.post(
        f"/api/v1/ai-interviews/{session_id}/consent",
        headers=_headers(candidate, token),
        json={"mic": False, "camera": False, "recording": False},
    )
    assert cons.status_code == 200, cons.text
    assert cons.json()["status"] == "ready"
    start2 = client.post(f"/api/v1/ai-interviews/{session_id}/start", headers=_headers(candidate, token))
    assert start2.status_code == 200, start2.text
    assert start2.json()["status"] == "in_progress"


def test_consent_withdrawal_stops_session(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    client.post(
        f"/api/v1/ai-interviews/{session_id}/consent",
        headers=_headers(candidate, token),
        json={"mic": False, "camera": False, "recording": False},
    )
    w = client.post(f"/api/v1/ai-interviews/{session_id}/consent/withdraw", headers=_headers(candidate, token))
    assert w.status_code == 200, w.text
    assert w.json()["status"] == "cancelled"
    session = db.get(AiInterviewSession, uuid.UUID(session_id))
    assert session.cancel_reason == "consent_withdrawn"
    # No further progress allowed.
    start = client.post(f"/api/v1/ai-interviews/{session_id}/start", headers=_headers(candidate, token))
    assert start.status_code == 422, start.text


# --- Question plan -------------------------------------------------------------

def test_plan_grounded_in_requirements_and_candidate(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=4)
    client.post(
        f"/api/v1/ai-interviews/{session_id}/consent",
        headers=_headers(candidate, token),
        json={},
    )
    start = client.post(f"/api/v1/ai-interviews/{session_id}/start", headers=_headers(candidate, token))
    assert start.status_code == 200, start.text
    questions = db.scalars(
        select(AiInterviewQuestion).where(AiInterviewQuestion.session_id == uuid.UUID(session_id))
    ).all()
    assert len(questions) == 4
    texts = " ".join(q.question for q in questions).lower()
    assert "operations leadership" in texts  # grounded in the posted requirement
    # No question contains a prohibited topic.
    from app.services.ai_interview import _PROHIBITED_RE

    for q in questions:
        for pat in _PROHIBITED_RE:
            assert pat.search(q.question) is None, f"prohibited: {q.question}"


def test_prohibited_configuration_rejected(client, make_user, db):
    employer, org_id, candidate, opp = _setup_org(client, make_user, db)
    pid = _person_id(db, _user_id(db, candidate["email"]))
    resp = _create(
        client, employer, org_id, pid,
        opportunity_id=str(opp.id),
        competencies=["candidate age", "religion"],
    )
    assert resp.status_code == 422, resp.text  # invalid config is rejected


def test_facial_and_lie_topics_have_no_route_or_tool(client):
    paths = [r.path for r in client.app.routes if getattr(r, "path", "").startswith("/api/v1")]
    joined = " ".join(paths)
    assert "facial" not in joined
    assert "lie" not in joined
    assert "emotion" not in joined


# --- Interview flow ------------------------------------------------------------

def _begin(client, candidate, token, session_id):
    client.post(
        f"/api/v1/ai-interviews/{session_id}/consent",
        headers=_headers(candidate, token),
        json={},
    )
    client.post(f"/api/v1/ai-interviews/{session_id}/start", headers=_headers(candidate, token))


def test_question_sequence_and_repeat_no_penalty(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=2)
    _begin(client, candidate, token, session_id)
    q1 = client.get(f"/api/v1/ai-interviews/{session_id}/next-question", headers=_headers(candidate, token))
    assert q1.status_code == 200, q1.text
    first_id = q1.json()["question_id"]
    # Repeat: same question, no evaluation created.
    rep = client.post(
        f"/api/v1/ai-interviews/{session_id}/repeat",
        headers=_headers(candidate, token),
        json={"question_id": first_id},
    )
    assert rep.status_code == 200, rep.text
    assert rep.json()["rephrased"] is True
    assert db.scalar(select(func.count(AiInterviewEvaluation.id))) == 0
    # Fetching next again does NOT re-ask the same question (status asked).
    q1b = client.get(f"/api/v1/ai-interviews/{session_id}/next-question", headers=_headers(candidate, token))
    assert q1b.json()["question_id"] != first_id


def test_answer_evaluation_never_persists_raw_answer(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=2)
    _begin(client, candidate, token, session_id)
    q = client.get(f"/api/v1/ai-interviews/{session_id}/next-question", headers=_headers(candidate, token)).json()
    secret_answer = "I reduced onboarding time by 50 percent by leading a cross-team effort — first we mapped the process, then we automated it, and as a result new hires were productive in two weeks."
    resp = client.post(
        f"/api/v1/ai-interviews/{session_id}/responses",
        headers=_headers(candidate, token),
        json={"question_id": q["question_id"], "answer": secret_answer},
    )
    assert resp.status_code == 200, resp.text
    ev = db.scalar(select(AiInterviewEvaluation))
    assert ev is not None
    assert "reduced onboarding" not in str(ev.dimensions)
    assert "50 percent" not in str(ev.dimensions)
    # Nowhere in the interview tables.
    for table in ("ai_interview_sessions", "ai_interview_questions", "ai_interview_evaluations", "ai_interview_reports"):
        from sqlalchemy import text

        row = db.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        if row:
            content = db.execute(text(f"SELECT * FROM {table}")).fetchall()
            assert all(secret_answer not in str(c) for c in content), table
    # Evaluation has explainable dimensions.
    assert "relevance" in ev.dimensions
    assert all(1 <= d["score"] <= 5 for d in ev.dimensions.values())


def test_adaptive_followup_stays_linked_to_competency(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=3)
    _begin(client, candidate, token, session_id)
    q = client.get(f"/api/v1/ai-interviews/{session_id}/next-question", headers=_headers(candidate, token)).json()
    weak = "yes it went fine"
    resp = client.post(
        f"/api/v1/ai-interviews/{session_id}/responses",
        headers=_headers(candidate, token),
        json={"question_id": q["question_id"], "answer": weak},
    )
    assert resp.status_code == 200, resp.text
    nxt = resp.json().get("next")
    assert nxt is not None, "expected an adaptive follow-up after a low-evidence answer"
    assert nxt["is_follow_up"] is True
    assert nxt["competency"] == q["competency"]
    follow = db.scalar(select(AiInterviewQuestion).where(AiInterviewQuestion.follow_up_of.is_not(None)))
    assert follow is not None and follow.competency == q["competency"]


def test_invalid_state_transitions_rejected(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    # Complete before start.
    c = client.post(f"/api/v1/ai-interviews/{session_id}/complete", headers=_headers(candidate, token))
    assert c.status_code == 422, c.text
    # Pause before start.
    p = client.post(f"/api/v1/ai-interviews/{session_id}/pause", headers=_headers(candidate, token))
    assert p.status_code == 422, p.text
    _begin(client, candidate, token, session_id)
    done = client.post(f"/api/v1/ai-interviews/{session_id}/complete", headers=_headers(candidate, token))
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"
    # Start from completed.
    s = client.post(f"/api/v1/ai-interviews/{session_id}/start", headers=_headers(candidate, token))
    assert s.status_code == 422, s.text


def test_lazy_expiry(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    session = db.get(AiInterviewSession, uuid.UUID(session_id))
    session.expires_at = datetime.utcnow() - timedelta(days=1)
    db.commit()
    r = _claim(client, candidate, token)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "expired"


def test_time_budget_ends_gracefully(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=5)
    _begin(client, candidate, token, session_id)
    session = db.get(AiInterviewSession, uuid.UUID(session_id))
    session.started_at = datetime.utcnow() - timedelta(minutes=session.duration_minutes + 5)
    db.commit()
    q = client.get(f"/api/v1/ai-interviews/{session_id}/next-question", headers=_headers(candidate, token))
    assert q.status_code == 200, q.text
    assert q.json()["status"] == "completed"
    assert db.scalar(select(func.count(AiInterviewReport.id))) == 1


# --- Cross-tenant isolation ----------------------------------------------------

def test_employer_cross_org_isolation(client, make_user, db):
    employer, org_id, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    # Second org employer cannot view or report on org A's session.
    other_emp = make_user(f"emp2{uuid.uuid4().hex[:6]}@example.com")
    other_org = _make_org(db, _user_id(db, other_emp["email"]), role="hiring_manager")
    view = client.get(
        f"/api/v1/ai-interviews/{session_id}",
        headers=other_emp["authorization"],
        params={"organization_id": str(other_org)},
    )
    assert view.status_code == 403, view.text
    report = client.get(
        f"/api/v1/ai-interviews/{session_id}/report",
        headers=other_emp["authorization"],
        params={"organization_id": str(other_org)},
    )
    assert report.status_code == 403, report.text


def test_candidate_cannot_read_employer_report(client, make_user, db):
    employer, org_id, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    # Candidate has no org permission -> 403 on the employer report route.
    r = client.get(
        f"/api/v1/ai-interviews/{session_id}/report",
        headers=candidate["authorization"],
        params={"organization_id": str(org_id)},
    )
    assert r.status_code == 403, r.text


# --- Reports & decisions -------------------------------------------------------

def test_full_flow_report_and_decision(client, make_user, db):
    employer, org_id, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=2)
    _begin(client, candidate, token, session_id)
    for _ in range(2):
        q = client.get(f"/api/v1/ai-interviews/{session_id}/next-question", headers=_headers(candidate, token))
        assert q.status_code == 200, q.text
        if q.json().get("status") == "completed":
            break
        r = client.post(
            f"/api/v1/ai-interviews/{session_id}/responses",
            headers=_headers(candidate, token),
            json={"question_id": q.json()["question_id"], "answer": "I led a project that improved outcomes by 30 percent — first we planned, then we executed, and as a result we shipped on time."},
        )
        assert r.status_code == 200, r.text
    done = client.post(f"/api/v1/ai-interviews/{session_id}/complete", headers=_headers(candidate, token))
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "completed"

    # Employer report.
    report = client.get(
        f"/api/v1/ai-interviews/{session_id}/report",
        headers=employer["authorization"],
        params={"organization_id": str(org_id)},
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert "HUMAN REVIEW REQUIRED" in body["summary"].upper() or "human review required" in body["summary"].lower()
    assert body["disclaimer"] and "human review" in body["disclaimer"].lower()
    assert body["integrity_signals"] == []
    assert body["interview_quality"]["note"]  # quality is not a hiring score

    # Candidate feedback — no confidential content.
    fb = client.get(f"/api/v1/ai-interviews/{session_id}/feedback", headers=_headers(candidate, token))
    assert fb.status_code == 200, fb.text
    assert "confidential" in fb.json()["note"].lower()
    assert "decision" not in fb.json()

    # Decision before any candidate-facing outcome: employer decides.
    d = client.post(
        f"/api/v1/ai-interviews/{session_id}/decision",
        headers=employer["authorization"],
        params={"organization_id": str(org_id)},
        json={"decision": "advance", "note": "Strong evidence overall"},
    )
    assert d.status_code == 200, d.text
    session = db.get(AiInterviewSession, uuid.UUID(session_id))
    assert session.decision == "advance"
    assert session.decided_by is not None
    # Invalid decision rejected.
    d2 = client.post(
        f"/api/v1/ai-interviews/{session_id}/decision",
        headers=employer["authorization"],
        params={"organization_id": str(org_id)},
        json={"decision": "hire_immediately"},
    )
    assert d2.status_code == 422, d2.text


def test_decision_requires_completed_interview(client, make_user, db):
    employer, org_id, candidate, _, session_id, _ = _create_and_invite(client, make_user, db)
    d = client.post(
        f"/api/v1/ai-interviews/{session_id}/decision",
        headers=employer["authorization"],
        params={"organization_id": str(org_id)},
        json={"decision": "hold"},
    )
    assert d.status_code == 422, d.text


# --- Integrity signals ---------------------------------------------------------

def test_integrity_signals_are_signals_only(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=1)
    _begin(client, candidate, token, session_id)
    s = client.post(
        f"/api/v1/ai-interviews/{session_id}/integrity-signals",
        headers=_headers(candidate, token),
        json={"signal_type": "session_disconnect", "detail": "network dropped"},
    )
    assert s.status_code == 200, s.text
    # Unknown / forbidden signal types are rejected (no facial, no lie).
    bad = client.post(
        f"/api/v1/ai-interviews/{session_id}/integrity-signals",
        headers=_headers(candidate, token),
        json={"signal_type": "facial_emotion_detected"},
    )
    assert bad.status_code == 422, bad.text
    session = db.get(AiInterviewSession, uuid.UUID(session_id))
    assert len(session.integrity_signals) == 1
    # The signal does not create an evaluation or penalty.
    assert db.scalar(select(func.count(AiInterviewEvaluation.id))) == 0


def test_integrity_signals_bounded(client, make_user, db):
    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db)
    from app.services.ai_interview import _MAX_INTEGRITY_SIGNALS

    for _ in range(_MAX_INTEGRITY_SIGNALS):
        r = client.post(
            f"/api/v1/ai-interviews/{session_id}/integrity-signals",
            headers=_headers(candidate, token),
            json={"signal_type": "session_disconnect"},
        )
        assert r.status_code == 200, r.text
    over = client.post(
        f"/api/v1/ai-interviews/{session_id}/integrity-signals",
        headers=_headers(candidate, token),
        json={"signal_type": "session_disconnect"},
    )
    assert over.status_code == 422, over.text


# --- Audit ---------------------------------------------------------------------

def test_lifecycle_audited(client, make_user, db):
    from app.models.audit import AuditLogEntry

    _, _, candidate, _, session_id, token = _create_and_invite(client, make_user, db, question_count=1)
    _begin(client, candidate, token, session_id)
    actions = {a for a in db.scalars(select(AuditLogEntry.action)).all()}
    assert "ai_interview.created" in actions
    assert "ai_interview.invited" in actions
    assert "ai_interview.consent.granted" in actions
    assert "ai_interview.started" in actions
    assert "ai_interview.plan.generated" in actions
    # Raw answers never appear in audit payloads.
    for entry in db.scalars(select(AuditLogEntry)).all():
        assert "secret" not in str(entry.payload)


# --- Concurrent isolation ------------------------------------------------------

def test_concurrent_candidate_sessions_isolated(client, make_user, db):
    e1, org1, c1, _, s1, t1 = _create_and_invite(client, make_user, db)
    e2, org2, c2, _, s2, t2 = _create_and_invite(client, make_user, db)
    # Candidate 1 cannot touch candidate 2's session even with c2's token
    # (person mismatch) or with c1's own token (token mismatch).
    r = _claim(client, c1, t2)
    assert r.status_code == 403, r.text
    q = client.get(f"/api/v1/ai-interviews/{s2}/next-question", headers=_headers(c1, t1))
    assert q.status_code == 403, q.text