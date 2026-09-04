"""Wave 5 — Super Admin / governance / finance contract.

Isolated sqlite TestClient. Never connects to live Supabase.
Run from backend/: .venv/bin/python ../scripts/wave5_admin_e2e.py
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import timedelta
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

from app.core.timeutil import utc_now_naive  # noqa: E402
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


def _user_id(engine, email: str):
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        return user.id


def _platform_role(engine, email: str, role: str) -> None:
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        org = Organization(
            name=f"DEV Platform {role} {uuid.uuid4().hex[:6]}",
            slug=f"dev-plat-{role}-{uuid.uuid4().hex[:6]}",
            kind="platform",
        )
        db.add(org)
        db.flush()
        db.add(
            Membership(
                user_id=user.id,
                organization_id=org.id,
                role_code=role,
                created_by=user.id,
            )
        )
        db.commit()


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
        json={"email": "dev+wave5.candidate@example.com", "password": password, "full_name": "DEV Wave5 Candidate"},
    )
    check("register candidate", cand.status_code == 201, f"status={cand.status_code}")
    headers_c = _auth(cand.json()["access_token"])
    cand_id = str(_user_id(engine, "dev+wave5.candidate@example.com"))

    emp = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+wave5.employer@example.com", "password": password, "full_name": "DEV Wave5 Employer"},
    )
    headers_e = _auth(emp.json()["access_token"])
    org = client.post(
        "/api/v1/organizations",
        headers=headers_e,
        json={"name": "DEV_WAVE5_ORG", "slug": "dev-wave5-org", "kind": "employer"},
    )
    check("create employer org", org.status_code == 201)

    admin = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+wave5.admin@example.com", "password": password, "full_name": "DEV Wave5 Admin"},
    )
    headers_a = _auth(admin.json()["access_token"])
    _platform_role(engine, "dev+wave5.admin@example.com", "super_admin")

    approver = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+wave5.approver@example.com", "password": password, "full_name": "DEV Wave5 Approver"},
    )
    headers_p = _auth(approver.json()["access_token"])
    _platform_role(engine, "dev+wave5.approver@example.com", "enforcement_manager")

    finance = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+wave5.finance@example.com", "password": password, "full_name": "DEV Wave5 Finance"},
    )
    headers_f = _auth(finance.json()["access_token"])
    _platform_role(engine, "dev+wave5.finance@example.com", "finance")

    support = client.post(
        "/api/v1/auth/register",
        json={"email": "dev+wave5.support@example.com", "password": password, "full_name": "DEV Wave5 Support"},
    )
    headers_s = _auth(support.json()["access_token"])
    _platform_role(engine, "dev+wave5.support@example.com", "customer_support")

    # --- RBAC: candidate / employer cannot enter Admin APIs
    denied = client.get("/api/v1/governance/dashboard", headers=headers_c)
    check("candidate cannot access Admin dashboard", denied.status_code == 403, f"status={denied.status_code}")
    denied = client.get("/api/v1/governance/dashboard", headers=headers_e)
    check("employer cannot access Admin dashboard", denied.status_code == 403, f"status={denied.status_code}")

    dash = client.get("/api/v1/governance/dashboard", headers=headers_a)
    check("DEV admin dashboard", dash.status_code == 200, f"status={dash.status_code}")

    # --- Candidate files a case (any authenticated user)
    report = client.post(
        "/api/v1/governance/reports",
        headers=headers_c,
        json={
            "target_type": "conversation",
            "target_id": str(uuid.uuid4()),
            "category": "harassment",
            "severity": "high",
            "description": "DEV Wave5 fixture: outreach pressure during a conversation.",
        },
    )
    check("candidate files governance case", report.status_code == 201, f"status={report.status_code}")
    case_id = report.json()["id"]

    hidden = client.get(f"/api/v1/governance/reports/{case_id}", headers=headers_c)
    check("candidate cannot read moderator case detail", hidden.status_code == 403)

    case = client.get(f"/api/v1/governance/reports/{case_id}", headers=headers_a)
    check("admin reads case", case.status_code == 200)
    check("case payload has no password material", "password" not in case.text.lower())

    # --- Assignment
    assigned = client.post(
        f"/api/v1/governance/reports/{case_id}/assign",
        headers=headers_a,
        json={"moderator_user_id": str(_user_id(engine, "dev+wave5.admin@example.com"))},
    )
    check("case assignment", assigned.status_code == 200, f"status={assigned.status_code}")

    # --- Finance / support cannot use governance controls
    denied = client.get("/api/v1/governance/dashboard", headers=headers_f)
    check("finance cannot access governance dashboard", denied.status_code == 403)
    denied = client.post(
        f"/api/v1/governance/reports/{case_id}/assign",
        headers=headers_s,
        json={"moderator_user_id": str(_user_id(engine, "dev+wave5.support@example.com"))},
    )
    check("support cannot assign governance cases", denied.status_code == 403)

    # --- Enforcement proposal + approval boundary
    propose = client.post(
        "/api/v1/enforcement/actions",
        headers=headers_a,
        json={
            "action_type": "suspension",
            "scope": "account",
            "reason_code": "policy_violation",
            "target_user_id": cand_id,
            "case_id": case_id,
            "effective_at": (utc_now_naive() - timedelta(seconds=1)).isoformat(),
        },
    )
    check("enforcement proposal", propose.status_code == 201, f"status={propose.status_code}")
    action_id = propose.json()["id"]

    self_approve = client.post(
        f"/api/v1/enforcement/actions/{action_id}/approve",
        headers=headers_a,
        json={"approval_note": "Creator attempting self-approval"},
    )
    check("creator cannot approve own suspension", self_approve.status_code == 403, f"status={self_approve.status_code}")

    denied = client.post(
        f"/api/v1/enforcement/actions/{action_id}/approve",
        headers=headers_f,
        json={"approval_note": "Finance attempting approval"},
    )
    check("finance cannot approve enforcement", denied.status_code == 403)

    approved = client.post(
        f"/api/v1/enforcement/actions/{action_id}/approve",
        headers=headers_p,
        json={"approval_note": "Second operator approval"},
    )
    check("second operator approves enforcement", approved.status_code == 200, f"status={approved.status_code}")
    check("enforcement became active", approved.json().get("status") == "active", str(approved.json().get("status")))

    # --- Appeal + decision
    limited = client.post("/api/v1/auth/login", json={"email": "dev+wave5.candidate@example.com", "password": password})
    headers_limited = _auth(limited.json()["access_token"]) if limited.status_code == 200 else headers_c
    appeal = client.post(
        "/api/v1/enforcement/appeals",
        headers=headers_limited,
        json={
            "enforcement_action_id": action_id,
            "reason_code": "wrong_target",
            "statement": "DEV Wave5 fixture: this enforcement was applied in error.",
        },
    )
    check("appeal submitted", appeal.status_code == 201, f"status={appeal.status_code}")
    appeal_id = appeal.json()["id"]
    check("appellant cannot see review_note", appeal.json().get("review_note") in (None, ""))

    assigned_appeal = client.post(
        f"/api/v1/enforcement/appeals/{appeal_id}/assign",
        headers=headers_a,
        json={"reviewer_id": str(_user_id(engine, "dev+wave5.approver@example.com"))},
    )
    check("appeal assignment", assigned_appeal.status_code == 200, f"status={assigned_appeal.status_code}")

    decided = client.post(
        f"/api/v1/enforcement/appeals/{appeal_id}/decide",
        headers=headers_p,
        json={
            "decision": "accepted",
            "decision_note": "Enforcement applied in error; access restored.",
            "review_note": "Internal governance note — never for the appellant.",
        },
    )
    check("appeal decision", decided.status_code == 200, f"status={decided.status_code}")
    check("superseding reinstatement present", bool(decided.json().get("superseding_action_id")))

    # --- Audit
    audit = client.get("/api/v1/governance/audit?page_size=10", headers=headers_a)
    check("admin audit", audit.status_code == 200)
    restored = client.post("/api/v1/auth/login", json={"email": "dev+wave5.candidate@example.com", "password": password})
    headers_restored = _auth(restored.json()["access_token"]) if restored.status_code == 200 else headers_c
    denied = client.get("/api/v1/governance/audit", headers=headers_restored)
    check("candidate cannot read platform audit", denied.status_code == 403, f"status={denied.status_code}")
    if audit.status_code == 200:
        blob = audit.text.lower()
        check("audit has no password material", "password" not in blob)

    # --- Finance boundary
    fin = client.get("/api/v1/finance/transactions", headers=headers_f)
    check("finance can read transactions", fin.status_code == 200, f"status={fin.status_code}")
    denied = client.get("/api/v1/finance/transactions", headers=headers_a)
    # super_admin has finance.read — that is allowed. Employer/support/candidate must fail.
    denied = client.get("/api/v1/finance/transactions", headers=headers_e)
    check("employer cannot read platform finance", denied.status_code == 403)
    denied = client.get("/api/v1/finance/transactions", headers=headers_s)
    check("support cannot read platform finance", denied.status_code == 403)
    denied = client.post(
        "/api/v1/finance/refunds",
        headers=headers_s,
        json={"transaction_id": str(uuid.uuid4()), "amount": "1.00", "reason": "no"},
    )
    check("support cannot authorize refunds", denied.status_code in (403, 404, 422), f"status={denied.status_code}")

    # --- Teams (routing, not authz)
    teams = client.get("/api/v1/governance/teams", headers=headers_a)
    check("governance teams", teams.status_code == 200)

    unauth = client.get("/api/v1/governance/dashboard")
    check("unauthenticated Admin denied", unauth.status_code == 401)

    print("")
    if failures:
        print("WAVE5 SUPER ADMIN E2E: FAIL")
        print("Failed:", ", ".join(failures))
        sys.exit(1)
    print("WAVE5 SUPER ADMIN E2E: PASS")


if __name__ == "__main__":
    run()
