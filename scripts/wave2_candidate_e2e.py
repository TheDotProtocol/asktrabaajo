"""Wave 2 — Candidate OS journey against the canonical API.

Isolated sqlite TestClient. Never connects to live Supabase.
Run from backend/: .venv/bin/python ../scripts/wave2_candidate_e2e.py
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.catalog import seed_catalog  # noqa: E402
from app.models import (  # noqa: F401,E402
    Membership,
    Organization,
    PersonProfile,
    RefreshToken,
    User,
)
from app.models.career import Interview, JobApplication, Offer, Opportunity  # noqa: E402
from app.models.governance import GOVERNANCE_TEAM_SEEDS, GovernanceTeam  # noqa: E402


def _engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(eng, "connect")
    def _enable_sqlite_fks(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    with Session(eng) as session:
        seed_catalog(session)
        for slug, name, description in GOVERNANCE_TEAM_SEEDS:
            exists = session.scalar(select(GovernanceTeam).where(GovernanceTeam.slug == slug))
            if exists is None:
                session.add(GovernanceTeam(slug=slug, name=name, description=description))
        session.commit()
    return eng


def _client(engine):
    def _override_get_db():
        session = Session(engine)
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _add_opportunity(engine, **kwargs) -> str:
    with Session(engine) as session:
        opp = Opportunity(
            id=uuid.uuid4(),
            company_name=kwargs.get("company_name", "DEV Demo Co"),
            title=kwargs.get("title", "Platform Engineer"),
            summary=kwargs.get("summary", "Development catalogue role — not a real employer."),
            skills_required=kwargs.get("skills_required", ["python", "sql"]),
            industry="Technology",
            work_mode="hybrid",
            country="UAE",
            city="Dubai",
            seniority="senior",
            experience_level="4+ years",
            status="active",
            is_approved=True,
            source="platform",
        )
        session.add(opp)
        session.commit()
        return str(opp.id)


def run() -> None:
    engine = _engine()
    client = _client(engine)
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}{(' — ' + detail) if detail else ''}")
        if not ok:
            failures.append(name)

    password = "correct-horse-battery"
    email = "dev+candidate.wave2@example.com"
    other_email = "dev+other.wave2@example.com"

    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "DEV Wave2 Candidate"},
    )
    check("register", reg.status_code == 201, f"status={reg.status_code} body={reg.text[:160]}")
    if reg.status_code != 201:
        print("\nWAVE2 CANDIDATE E2E: FAIL (register)")
        sys.exit(1)
    access = reg.json()["access_token"]

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    check("login", login.status_code == 200)
    access = login.json()["access_token"]
    headers = _auth(access)

    dash = client.get("/api/v1/jobseeker/dashboard", headers=headers)
    check("dashboard", dash.status_code == 200)
    check("dashboard empty stats honest", (dash.json().get("stats") or {}).get("applications", 0) == 0)

    work = client.get("/api/v1/work-id", headers=headers)
    check("work-id", work.status_code == 200)
    profile = client.put(
        "/api/v1/work-id/profile",
        headers=headers,
        json={"headline": "DEV candidate — not a real person", "city": "Dubai"},
    )
    check("work-id profile", profile.status_code == 200)
    skill = client.put(
        "/api/v1/work-id/skills",
        headers=headers,
        json={"skill_name": "Python", "level": "advanced", "years_experience": 5},
    )
    check("work-id skill", skill.status_code == 200)
    client.put(
        "/api/v1/work-id/skills",
        headers=headers,
        json={"skill_name": "SQL", "level": "intermediate", "years_experience": 3},
    )

    goal = client.post(
        "/api/v1/jobseeker/goals",
        headers=headers,
        json={"title": "DEV goal", "target_role": "Platform Engineer", "is_primary": True},
    )
    check("career goal", goal.status_code in {200, 201}, f"status={goal.status_code}")

    questions = client.get("/api/v1/jobseeker/work-dna/questions", headers=headers)
    check("work-dna questions", questions.status_code == 200 and len(questions.json()) >= 3)
    answers = {q["key"]: q["options"][0]["value"] for q in questions.json()}
    dna = client.post("/api/v1/jobseeker/work-dna/assessments", headers=headers, json={"answers": answers})
    check("work-dna assess", dna.status_code == 201, f"status={dna.status_code}")

    opp_id = _add_opportunity(engine)
    opps = client.get("/api/v1/jobseeker/opportunities", headers=headers)
    check("opportunities", opps.status_code == 200 and opps.json().get("total", 0) >= 1)

    detail = client.get(f"/api/v1/jobseeker/opportunities/{opp_id}", headers=headers)
    check("opportunity detail", detail.status_code == 200)

    applied = client.post(
        "/api/v1/jobseeker/applications",
        headers=headers,
        json={"opportunity_id": opp_id, "cover_note": "DEV apply"},
    )
    check("apply", applied.status_code in {200, 201}, f"status={applied.status_code}")
    app_id = applied.json()["id"]

    apps = client.get("/api/v1/jobseeker/applications", headers=headers)
    check("applications list", apps.status_code == 200 and len(apps.json()) == 1)
    app_detail = client.get(f"/api/v1/jobseeker/applications/{app_id}", headers=headers)
    check("application detail", app_detail.status_code == 200)

    advisor = client.get("/api/v1/jobseeker/advisor", headers=headers)
    check("advisor snapshot", advisor.status_code == 200)
    for path in (
        "/api/v1/career-advisor/digest",
        "/api/v1/career-advisor/gaps",
        "/api/v1/career-advisor/paths",
        "/api/v1/career-advisor/action-plan",
        "/api/v1/career-advisor/opportunities?mode=strong",
        "/api/v1/career-advisor/opportunities?mode=potential",
        "/api/v1/career-advisor/opportunities?mode=transition",
        "/api/v1/career-advisor/opportunities?mode=explore",
    ):
        res = client.get(path, headers=headers)
        check(f"career-advisor {path.split('/')[-1].split('?')[0]}", res.status_code == 200, f"status={res.status_code}")

    docs = client.get("/api/v1/documents", headers=headers)
    check("documents empty", docs.status_code == 200 and docs.json() == [])
    created_doc = client.post("/api/v1/documents", headers=headers, json={"name": "DEV resume", "doc_type": "resume"})
    check("document create", created_doc.status_code in {200, 201}, f"status={created_doc.status_code}")

    privacy = client.get("/api/v1/work-id/privacy", headers=headers)
    check("privacy", privacy.status_code == 200)
    notes = client.get("/api/v1/jobseeker/notifications", headers=headers)
    check("notifications", notes.status_code == 200)
    comms = client.get("/api/v1/jobseeker/communications", headers=headers)
    check("communications", comms.status_code == 200)

    with Session(engine) as session:
        db_app = session.get(JobApplication, uuid.UUID(app_id))
        session.add(
            Interview(
                application_id=db_app.id,
                scheduled_at=datetime.utcnow() + timedelta(days=2),
                duration_minutes=45,
                mode="video",
                status="scheduled",
                interviewer_name="DEV Hiring Manager",
            )
        )
        session.add(
            Offer(
                application_id=db_app.id,
                status="pending",
                salary_amount=100000,
                salary_currency="USD",
                start_date=date(2026, 10, 1),
            )
        )
        session.commit()

    interviews = client.get("/api/v1/jobseeker/interviews", headers=headers)
    check("interviews", interviews.status_code == 200 and len(interviews.json()) == 1)
    interview_id = interviews.json()[0]["id"]
    reschedule = client.post(
        f"/api/v1/jobseeker/interviews/{interview_id}/reschedule-request",
        headers=headers,
        json={"reason": "DEV conflict — isolated fixture"},
    )
    check("reschedule request", reschedule.status_code == 200, f"status={reschedule.status_code}")

    offers = client.get("/api/v1/jobseeker/offers", headers=headers)
    check("offers", offers.status_code == 200 and len(offers.json()) == 1)
    offer_id = offers.json()[0]["id"]
    accept = client.post(
        f"/api/v1/jobseeker/offers/{offer_id}/decision",
        headers=headers,
        json={"decision": "accepted"},
    )
    check("accept offer", accept.status_code == 200 and accept.json()["status"] == "accepted")

    other = client.post(
        "/api/v1/auth/register",
        json={"email": other_email, "password": password, "full_name": "DEV Wave2 Other"},
    )
    other_headers = _auth(other.json()["access_token"])
    other_apps = client.get("/api/v1/jobseeker/applications", headers=other_headers)
    check("cross-user applications empty", other_apps.status_code == 200 and other_apps.json() == [])
    other_detail = client.get(f"/api/v1/jobseeker/applications/{app_id}", headers=other_headers)
    check("cross-user application hidden", other_detail.status_code in {403, 404}, f"status={other_detail.status_code}")
    other_offer = client.post(
        f"/api/v1/jobseeker/offers/{offer_id}/decision",
        headers=other_headers,
        json={"decision": "declined"},
    )
    check("cross-user offer hidden", other_offer.status_code in {403, 404}, f"status={other_offer.status_code}")
    other_docs = client.get("/api/v1/documents", headers=other_headers)
    check("cross-user documents empty", other_docs.status_code == 200 and other_docs.json() == [])

    anon = client.get("/api/v1/jobseeker/dashboard")
    check("unauthenticated denied", anon.status_code == 401)

    if failures:
        print(f"\nWAVE2 CANDIDATE E2E: FAIL ({len(failures)} checks)")
        sys.exit(1)
    print("\nWAVE2 CANDIDATE E2E: PASS")


if __name__ == "__main__":
    run()
