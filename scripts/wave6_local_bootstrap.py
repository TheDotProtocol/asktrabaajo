"""Wave 6 — isolated local SQLite bootstrap.

Creates backend/asktrabaajo_wave6.db with the canonical schema, catalog,
governance teams, and DEV-prefixed users. Never reads or writes hosted Supabase.

Run from repo root:
  backend/.venv/bin/python scripts/wave6_local_bootstrap.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
DB_PATH = BACKEND / "asktrabaajo_wave6.db"
sys.path.insert(0, str(BACKEND))

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["SECRET_KEY"] = "wave6-local-dev-only-not-for-hosted"
os.environ["AI_PROVIDER"] = "none"
os.environ["PAYMENT_PROVIDER"] = "mock"

from sqlalchemy import create_engine, event, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: F401,E402
from app.db.base import Base  # noqa: E402
from app.models.catalog import seed_catalog  # noqa: E402
from app.models import Membership, Organization, User  # noqa: E402
from app.models.governance import GOVERNANCE_TEAM_SEEDS, GovernanceTeam  # noqa: E402
from app.services.auth_service import register_user  # noqa: E402

DEV_PASSWORD = "Wave6-dev-local!"
USERS = (
    ("dev+wave6.candidate@example.com", "DEV Wave6 Candidate", None),
    ("dev+wave6.employer@example.com", "DEV Wave6 Employer", "employer"),
    ("dev+wave6.admin@example.com", "DEV Wave6 Admin", "admin"),
)


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()

    engine = create_engine(f"sqlite:///{DB_PATH}", future=True)

    @event.listens_for(engine, "connect")
    def _fk(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_catalog(db)
        for slug, name, description in GOVERNANCE_TEAM_SEEDS:
            if db.scalar(select(GovernanceTeam).where(GovernanceTeam.slug == slug)) is None:
                db.add(GovernanceTeam(slug=slug, name=name, description=description))
        db.commit()

        for email, name, kind in USERS:
            register_user(db, email=email, password=DEV_PASSWORD, full_name=name)
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            if kind == "employer":
                org = Organization(
                    name="DEV_WAVE6_ORG",
                    slug="dev-wave6-org",
                    kind="employer",
                )
                db.add(org)
                db.flush()
                db.add(
                    Membership(
                        user_id=user.id,
                        organization_id=org.id,
                        role_code="org_admin",
                        created_by=user.id,
                    )
                )
            if kind == "admin":
                org = Organization(
                    name="DEV Wave6 Platform",
                    slug="dev-wave6-platform",
                    kind="platform",
                )
                db.add(org)
                db.flush()
                db.add(
                    Membership(
                        user_id=user.id,
                        organization_id=org.id,
                        role_code="super_admin",
                        created_by=user.id,
                    )
                )
        db.commit()

    print(f"WAVE6 LOCAL DB: {DB_PATH}")
    print("DEV accounts (not production):")
    print(f"  candidate  dev+wave6.candidate@example.com  {DEV_PASSWORD}")
    print(f"  employer   dev+wave6.employer@example.com   {DEV_PASSWORD}")
    print(f"  admin      dev+wave6.admin@example.com      {DEV_PASSWORD}")


if __name__ == "__main__":
    main()
