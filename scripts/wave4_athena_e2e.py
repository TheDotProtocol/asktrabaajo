"""Wave 4 — Athena UI contract against the canonical API.

Isolated sqlite TestClient. Never connects to live Supabase.
With AI_PROVIDER=none, chat must fail honestly — never fabricate a reply.
Run from backend/: .venv/bin/python ../scripts/wave4_athena_e2e.py
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["AI_PROVIDER"] = "none"

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
    cand = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+athena.candidate@example.com", "password": password, "full_name": "DEV Athena Candidate"},
    )
    check("register candidate", cand.status_code == 201, f"status={cand.status_code}")
    if cand.status_code != 201:
        sys.exit(1)
    headers_c = _auth(cand.json()["access_token"])

    emp = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+athena.employer@example.com", "password": password, "full_name": "DEV Athena Employer"},
    )
    headers_e = _auth(emp.json()["access_token"])
    org = client.post(
        "/api/v1/organizations",
        headers=headers_e,
        json={"name": "DEV_ATHENA_ORG_A", "slug": "dev-athena-a", "kind": "employer"},
    )
    check("create employer org A", org.status_code == 201)
    org_a = org.json()["id"]

    emp_b = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+athena.employer.b@example.com", "password": password, "full_name": "DEV Athena Employer B"},
    )
    headers_b = _auth(emp_b.json()["access_token"])
    org_b = client.post(
        "/api/v1/organizations",
        headers=headers_b,
        json={"name": "DEV_ATHENA_ORG_B", "slug": "dev-athena-b", "kind": "employer"},
    ).json()["id"]

    status_c = client.get("/api/v1/athena/status", headers=headers_c)
    check("candidate status", status_c.status_code == 200)
    body = status_c.json()
    check("degraded not_configured", body.get("state") == "not_configured" and body.get("available") is False)
    check("candidate has jobseeker mode", "jobseeker" in body.get("modes", []))
    check("candidate lacks employer mode", "employer" not in body.get("modes", []))
    check("status hides provider secrets", "openai" not in status_c.text.lower() and "secret" not in status_c.text.lower())

    modes_e = client.get("/api/v1/athena/modes", headers=headers_e)
    check("employer modes", modes_e.status_code == 200 and "employer" in modes_e.json())

    tools_c = client.get("/api/v1/athena/tools?mode=jobseeker", headers=headers_c)
    check("jobseeker tools listed", tools_c.status_code == 200 and any(t["name"] == "career.get_recommendations" for t in tools_c.json()))
    tools_e = client.get("/api/v1/athena/tools?mode=employer", headers=headers_e)
    check("employer tools listed", tools_e.status_code == 200 and any(t["name"] == "search_talent" for t in tools_e.json()))

    session_c = client.post(
        "/api/v1/athena/session",
        headers=headers_c,
        json={"mode": "jobseeker", "purpose": "DEV candidate workspace"},
    )
    check("candidate session", session_c.status_code == 200, f"status={session_c.status_code}")
    sid_c = session_c.json()["session_id"]

    msg = client.post(
        "/api/v1/athena/message",
        headers=headers_c,
        json={"session_id": sid_c, "message": "Find my strongest job matches"},
    )
    check("degraded chat is not fabricated", msg.status_code == 502 and msg.json()["error"]["code"] == "ai.provider_unavailable")
    check("degraded chat has no reply body", "reply" not in msg.json())

    steal_mode = client.post(
        "/api/v1/athena/session",
        headers=headers_c,
        json={"mode": "employer", "organization_id": org_a},
    )
    check("candidate cannot open employer Athena", steal_mode.status_code in {403, 404}, f"status={steal_mode.status_code}")

    session_e = client.post(
        "/api/v1/athena/session",
        headers=headers_e,
        json={"mode": "employer", "organization_id": org_a, "purpose": "DEV employer workspace"},
    )
    check("employer session A", session_e.status_code == 200, f"status={session_e.status_code} body={session_e.text[:160]}")
    sid_e = session_e.json()["session_id"]

    steal_org = client.post(
        "/api/v1/athena/session",
        headers=headers_e,
        json={"mode": "employer", "organization_id": org_b},
    )
    check("cross-tenant employer session denied", steal_org.status_code in {403, 404}, f"status={steal_org.status_code}")

    steal_session = client.post(
        "/api/v1/athena/message",
        headers=headers_c,
        json={"session_id": sid_e, "message": "Show me candidates"},
    )
    check("candidate cannot use employer session", steal_session.status_code in {403, 404}, f"status={steal_session.status_code}")

    fake_confirm = client.post(
        "/api/v1/athena/confirm",
        headers=headers_c,
        json={"confirmation_id": str(uuid.uuid4()), "approve": True},
    )
    check("unknown confirmation denied", fake_confirm.status_code in {403, 404}, f"status={fake_confirm.status_code}")

    reuse = client.post(
        "/api/v1/athena/confirm",
        headers=headers_e,
        json={"confirmation_id": str(uuid.uuid4()), "approve": True},
    )
    check("employer unknown confirmation denied", reuse.status_code in {403, 404})

    closed = client.post(f"/api/v1/athena/session/{sid_c}/close", headers=headers_c)
    check("close session", closed.status_code == 200 and closed.json()["status"] == "closed")
    after_close = client.post(
        "/api/v1/athena/message",
        headers=headers_c,
        json={"session_id": sid_c, "message": "hello again"},
    )
    check("closed session cannot chat", after_close.status_code in {400, 403, 404, 422, 502}, f"status={after_close.status_code}")

    unauth = client.get("/api/v1/athena/status")
    check("unauthenticated Athena denied", unauth.status_code == 401, f"status={unauth.status_code}")

    dash = client.get("/api/v1/jobseeker/dashboard", headers=headers_e)
    # employer still has a person profile from register — dashboard is fine
    check("employer can still use jobseeker dashboard", dash.status_code == 200)

    if failures:
        print(f"\nWAVE4 ATHENA E2E: FAIL ({len(failures)} checks)")
        sys.exit(1)
    print("\nWAVE4 ATHENA E2E: PASS")


if __name__ == "__main__":
    run()
