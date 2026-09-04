"""Wave 7 — multi-portal DEV identity + RBAC boundaries.

Isolated sqlite TestClient. Never connects to hosted Supabase.
Does not use the owner Wave 7 password file.
Run from backend/: .venv/bin/python ../scripts/wave7_dev_e2e.py
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
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.catalog import seed_catalog  # noqa: E402
from app.models import Membership, Organization  # noqa: E402
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

    return eng


def _client(engine):
    Base.metadata.create_all(engine)

    def override():
        db = Session(engine)
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override
    with Session(engine) as db:
        seed_catalog(db)
        for slug, name, description in GOVERNANCE_TEAM_SEEDS:
            db.add(GovernanceTeam(slug=slug, name=name, description=description))
        db.commit()
    return TestClient(app)


def _auth(client: TestClient, email: str, password: str) -> dict:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    engine = _engine()
    client = _client(engine)
    password = "Wave7-e2e-local!"
    email = f"dev+wave7.{uuid.uuid4().hex[:8]}@example.com"
    other = f"dev+wave7.other.{uuid.uuid4().hex[:8]}@example.com"

    created = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "DEV Wave7 E2E"},
    )
    assert created.status_code == 201, created.text
    headers = _auth(client, email, password)

    org = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": "DEV Wave7 E2E Co", "kind": "employer"},
    )
    assert org.status_code == 201, org.text
    org_id = org.json()["id"]

    other_reg = client.post(
        "/api/v1/auth/register",
        json={"email": other, "password": password, "full_name": "DEV Other Employer"},
    )
    assert other_reg.status_code == 201, other_reg.text
    other_headers = _auth(client, other, password)
    other_org = client.post(
        "/api/v1/organizations",
        headers=other_headers,
        json={"name": "DEV Other Co", "kind": "employer"},
    )
    assert other_org.status_code == 201, other_org.text
    other_org_id = other_org.json()["id"]

    with Session(engine) as db:
        gov = Organization(
            name="DEV Wave7 Gov",
            slug=f"dev-wave7-gov-{uuid.uuid4().hex[:6]}",
            kind="government",
        )
        db.add(gov)
        db.flush()
        from sqlalchemy import select

        from app.models import User

        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        db.add(
            Membership(
                user_id=user.id,
                organization_id=gov.id,
                role_code="government_user",
                created_by=user.id,
            )
        )
        db.commit()

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    body = me.json()
    kinds = {m["organization_kind"] for m in body["memberships"]}
    assert "employer" in kinds
    assert "government" in kinds
    assert body["super_admin"] is False
    assert "workforce.aggregates.read" in body["permissions"]
    assert "admin.manage" not in body["permissions"]
    print("  [PASS] stacked memberships without god-mode")

    dash = client.get("/api/v1/jobseeker/dashboard", headers=headers)
    assert dash.status_code == 200, dash.text
    print("  [PASS] jobseeker dashboard")

    work = client.get("/api/v1/work-id", headers=headers)
    assert work.status_code == 200, work.text
    print("  [PASS] work-id")

    company = client.get(f"/api/v1/company/{org_id}/dashboard", headers=headers)
    assert company.status_code == 200, company.text
    print("  [PASS] employer dashboard")

    denied = client.get(f"/api/v1/company/{other_org_id}/dashboard", headers=headers)
    assert denied.status_code in {403, 404}, denied.text
    print(f"  [PASS] cross-tenant employer denied — {denied.status_code}")

    gov_admin = client.get("/api/v1/governance/dashboard", headers=headers)
    assert gov_admin.status_code == 403, gov_admin.text
    print("  [PASS] government membership does not open Super Admin")

    unauth = client.get("/api/v1/jobseeker/dashboard")
    assert unauth.status_code == 401, unauth.text
    print("  [PASS] unauthenticated denied")

    print("\nWAVE7 MULTI-PORTAL E2E: PASS")


if __name__ == "__main__":
    main()
