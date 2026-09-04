"""Wave 3 — Employer OS journey against the canonical API.

Isolated sqlite TestClient. Never connects to live Supabase.
Run from backend/: .venv/bin/python ../scripts/wave3_employer_e2e.py
"""
from __future__ import annotations

import os
import sys
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
from app.models import Membership, Organization, PersonProfile, RefreshToken, User  # noqa: F401,E402
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
    a = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+employer.a@example.com", "password": password, "full_name": "DEV Employer A"},
    )
    check("register employer A", a.status_code == 201, f"status={a.status_code}")
    if a.status_code != 201:
        sys.exit(1)
    headers_a = _auth(a.json()["access_token"])

    b = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+employer.b@example.com", "password": password, "full_name": "DEV Employer B"},
    )
    headers_b = _auth(b.json()["access_token"])

    cand = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+candidate.w3@example.com", "password": password, "full_name": "DEV Wave3 Candidate"},
    )
    headers_c = _auth(cand.json()["access_token"])
    client.put(
        "/api/v1/work-id/skills",
        headers=headers_c,
        json={"skill_name": "Python", "level": "advanced", "years_experience": 5},
    )
    client.put(
        "/api/v1/work-id/profile",
        headers=headers_c,
        json={"headline": "DEV candidate — not a real person", "city": "Dubai"},
    )

    org_a = client.post(
        "/api/v1/organizations",
        headers=headers_a,
        json={"name": "DEV_ORG_A", "slug": "dev-org-a", "kind": "employer"},
    )
    check("create DEV_ORG_A", org_a.status_code == 201, f"status={org_a.status_code} body={org_a.text[:160]}")
    org_a_id = org_a.json()["id"]
    org_b = client.post(
        "/api/v1/organizations",
        headers=headers_b,
        json={"name": "DEV_ORG_B", "slug": "dev-org-b", "kind": "employer"},
    )
    check("create DEV_ORG_B", org_b.status_code == 201)
    org_b_id = org_b.json()["id"]

    dash = client.get(f"/api/v1/company/{org_a_id}/dashboard", headers=headers_a)
    check("dashboard A", dash.status_code == 200 and dash.json()["open_jobs"] == 0)

    profile = client.patch(
        f"/api/v1/company/{org_a_id}/profile",
        headers=headers_a,
        json={"display_name": "DEV Org A", "city": "Dubai", "country": "UAE", "industry": "Technology"},
    )
    check("company profile", profile.status_code == 200, f"status={profile.status_code}")

    members = client.get(f"/api/v1/organizations/{org_a_id}/members", headers=headers_a)
    check("members list", members.status_code == 200 and len(members.json()["members"]) >= 1)

    job = client.post(
        f"/api/v1/company/{org_a_id}/jobs",
        headers=headers_a,
        json={
            "title": "DEV Platform Engineer",
            "summary": "Development fixture — not a real role.",
            "department": "Engineering",
            "skills_required": ["python"],
            "work_mode": "hybrid",
            "employment_type": "full_time",
            "city": "Dubai",
            "country": "UAE",
        },
    )
    check("create job draft", job.status_code == 201 and job.json()["status"] == "draft")
    job_id = job.json()["id"]

    published = client.post(f"/api/v1/company/{org_a_id}/jobs/{job_id}/publish", headers=headers_a)
    check("publish job", published.status_code == 200, f"status={published.status_code}")
    opp_id = published.json().get("opportunity_id")

    jobs = client.get(f"/api/v1/company/{org_a_id}/jobs", headers=headers_a)
    check("list jobs", jobs.status_code == 200 and len(jobs.json()) == 1)

    search = client.get(f"/api/v1/talent/{org_a_id}/candidates/search", headers=headers_a)
    check("talent search", search.status_code == 200)

    if opp_id:
        applied = client.post(
            "/api/v1/jobseeker/applications",
            headers=headers_c,
            json={"opportunity_id": opp_id, "cover_note": "DEV apply"},
        )
        check("candidate apply", applied.status_code in {200, 201}, f"status={applied.status_code}")
        app_id = applied.json()["id"]
    else:
        app_id = None
        check("candidate apply", False, "no opportunity_id after publish")

    apps = client.get(f"/api/v1/company/{org_a_id}/applications", headers=headers_a)
    check("pipeline", apps.status_code == 200)

    if app_id:
        review = client.get(f"/api/v1/company/{org_a_id}/applications/{app_id}", headers=headers_a)
        check("application detail", review.status_code == 200)
        doc = client.post(
            f"/api/v1/company/{org_a_id}/document-requests",
            headers=headers_a,
            json={"application_id": app_id, "document_type": "resume", "purpose": "DEV review"},
        )
        check("document request", doc.status_code in {200, 201}, f"status={doc.status_code}")
        offer = client.post(
            f"/api/v1/company/{org_a_id}/offers",
            headers=headers_a,
            json={"application_id": app_id, "salary_amount": 100000, "salary_currency": "USD"},
        )
        check("create offer", offer.status_code in {200, 201}, f"status={offer.status_code}")

    interviews = client.get(f"/api/v1/company/{org_a_id}/interviews", headers=headers_a)
    check("interviews list", interviews.status_code == 200)
    offers = client.get(f"/api/v1/company/{org_a_id}/offers", headers=headers_a)
    check("offers list", offers.status_code == 200)
    analytics = client.get(f"/api/v1/company/{org_a_id}/analytics", headers=headers_a)
    check("analytics", analytics.status_code == 200)
    billing = client.get("/api/v1/billing/plans", headers=headers_a)
    check("billing plans", billing.status_code == 200)
    pools = client.get(f"/api/v1/talent/{org_a_id}/pools", headers=headers_a)
    check("talent pools", pools.status_code == 200)
    comms = client.get(f"/api/v1/talent/{org_a_id}/communications", headers=headers_a)
    check("communications", comms.status_code == 200)
    ai = client.get(f"/api/v1/ai-interviews?organization_id={org_a_id}", headers=headers_a)
    check("ai interviews", ai.status_code == 200, f"status={ai.status_code}")

    # Cross-tenant: authorization failure, not empty success
    for path, label in (
        (f"/api/v1/company/{org_b_id}/dashboard", "dashboard"),
        (f"/api/v1/company/{org_b_id}/jobs", "jobs"),
        (f"/api/v1/company/{org_b_id}/applications", "applications"),
        (f"/api/v1/company/{org_b_id}/interviews", "interviews"),
        (f"/api/v1/company/{org_b_id}/offers", "offers"),
        (f"/api/v1/talent/{org_b_id}/pools", "pools"),
        (f"/api/v1/talent/{org_b_id}/communications", "communications"),
        (f"/api/v1/billing/subscription?organization_id={org_b_id}", "billing"),
    ):
        res = client.get(path, headers=headers_a)
        check(
            f"cross-tenant {label} denied",
            res.status_code in {403, 404},
            f"status={res.status_code}",
        )

    steal = client.post(
        f"/api/v1/company/{org_b_id}/jobs",
        headers=headers_a,
        json={"title": "Should fail"},
    )
    check("cross-tenant job create denied", steal.status_code in {403, 404}, f"status={steal.status_code}")

    # Candidate Wave 2 regression
    dash_c = client.get("/api/v1/jobseeker/dashboard", headers=headers_c)
    check("candidate dashboard still works", dash_c.status_code == 200)

    if failures:
        print(f"\nWAVE3 EMPLOYER E2E: FAIL ({len(failures)} checks)")
        sys.exit(1)
    print("\nWAVE3 EMPLOYER E2E: PASS")


if __name__ == "__main__":
    run()
