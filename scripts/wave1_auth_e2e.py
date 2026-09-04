"""Wave 1 — canonical auth contract used by the frontend session client.

Isolated sqlite TestClient. Never connects to live Supabase.
Run from backend/: .venv/bin/python ../scripts/wave1_auth_e2e.py
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
from app.models import (  # noqa: F401,E402
    Membership,
    Organization,
    PersonProfile,
    RefreshToken,
    User,
)
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

    # 1. registration
    email = "wave1.user@example.com"
    password = "correct-horse-battery"
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Wave One"},
    )
    check("registration", reg.status_code == 201, f"status={reg.status_code}")
    pair = reg.json()
    check("registration returns token pair", "access_token" in pair and "refresh_token" in pair)

    # 2. login
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    check("login", login.status_code == 200 and login.json().get("access_token"))
    access = login.json()["access_token"]
    refresh = login.json()["refresh_token"]

    # 3. invalid login
    bad = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})
    check("invalid login", bad.status_code == 401)

    # 4. me / session restoration analogue
    me = client.get("/api/v1/auth/me", headers=_auth(access))
    check("session me", me.status_code == 200 and me.json()["email"] == email)
    check("person created", me.json().get("person") is not None)

    # 5+6. refresh rotation
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    check("refresh", rotated.status_code == 200)
    new_access = rotated.json()["access_token"]
    new_refresh = rotated.json()["refresh_token"]
    check("refresh rotates tokens", new_access != access and new_refresh != refresh)

    # replay of old refresh must fail (family revoke)
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    check("failed refresh (replay)", replay.status_code == 401)

    # 7. failed refresh with garbage
    garbage = client.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 40})
    check("failed refresh (invalid)", garbage.status_code == 401)

    # 8. logout
    out = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    check("logout", out.status_code == 200)
    after = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    check("logout revokes refresh", after.status_code == 401)

    # re-login for remaining checks
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    access = login.json()["access_token"]

    # 9. protected route
    dash = client.get("/api/v1/jobseeker/dashboard", headers=_auth(access))
    check("protected jobseeker dashboard", dash.status_code == 200)

    for path, label in (
        ("/api/v1/jobseeker/opportunities", "opportunities"),
        ("/api/v1/jobseeker/applications", "applications"),
        ("/api/v1/jobseeker/interviews", "interviews"),
        ("/api/v1/jobseeker/offers", "offers"),
        ("/api/v1/jobseeker/work-dna", "work-dna"),
        ("/api/v1/jobseeker/communications", "communications"),
        ("/api/v1/work-id", "work-id"),
    ):
        res = client.get(path, headers=_auth(access))
        check(f"canonical page API {label}", res.status_code == 200, f"status={res.status_code}")

    # 10. unauthenticated
    anon = client.get("/api/v1/jobseeker/dashboard")
    check("unauthenticated access denied", anon.status_code == 401)

    # 12. organization context
    org = client.post(
        "/api/v1/organizations",
        headers=_auth(access),
        json={"name": "Wave1 Co", "kind": "employer"},
    )
    check("create organization", org.status_code == 201, f"status={org.status_code}")
    org_id = org.json()["id"]
    company = client.get(f"/api/v1/company/{org_id}/dashboard", headers=_auth(access))
    check("organization dashboard", company.status_code == 200)
    jobs = client.get(f"/api/v1/company/{org_id}/jobs", headers=_auth(access))
    check("company jobs", jobs.status_code == 200)
    pipeline = client.get(f"/api/v1/company/{org_id}/applications", headers=_auth(access))
    check("company pipeline", pipeline.status_code == 200)
    talent = client.get(
        f"/api/v1/talent/{org_id}/candidates/search", headers=_auth(access)
    )
    check("talent search", talent.status_code == 200, f"status={talent.status_code}")
    interviews = client.get(
        f"/api/v1/ai-interviews?organization_id={org_id}", headers=_auth(access)
    )
    check("ai interviews", interviews.status_code == 200, f"status={interviews.status_code}")
    billing = client.get("/api/v1/billing/plans", headers=_auth(access))
    check("billing plans", billing.status_code == 200)
    gov = client.get("/api/v1/governance/dashboard", headers=_auth(access))
    check(
        "governance denied to employer",
        gov.status_code == 403,
        f"status={gov.status_code}",
    )

    # 11+13. unauthorized / cross-org
    other = client.post(
        "/api/v1/auth/register",
        json={"email": "wave1.other@example.com", "password": password, "full_name": "Other Person"},
    )
    other_access = other.json()["access_token"]
    denied = client.get(f"/api/v1/company/{org_id}/dashboard", headers=_auth(other_access))
    check("cross-organization denial", denied.status_code in {403, 404}, f"status={denied.status_code}")

    finance = client.get("/api/v1/finance/transactions", headers=_auth(access))
    check("unauthorized finance role", finance.status_code == 403)

    if failures:
        print(f"\nWAVE1 AUTH E2E: FAIL ({len(failures)} checks)")
        sys.exit(1)
    print("\nWAVE1 AUTH E2E: PASS")


if __name__ == "__main__":
    run()
