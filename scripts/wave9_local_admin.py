"""Grant the local DEV inspector a platform membership.

Local SQLite only. Does not change production RBAC. Does not recreate the
database. Does not print or change the DEV password.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
DB_PATH = BACKEND / "asktrabaajo_wave6.db"
sys.path.insert(0, str(BACKEND))

os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH}")
os.environ.setdefault("SECRET_KEY", "wave6-local-dev-only-not-for-hosted")

from sqlalchemy import create_engine, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.models import Membership, Organization, User  # noqa: E402

EMAIL = "akumartrabaajo@gmail.com"
ORG_SLUG = "asktrabaajo-dev-platform"
ORG_NAME = "AskTrabaajo DEV Platform"


def ensure_local_super_admin(db: Session) -> None:
    user = db.scalar(select(User).where(User.email == EMAIL))
    if user is None:
        raise SystemExit(f"DEV inspector {EMAIL} is not in {DB_PATH}")
    org = db.scalar(select(Organization).where(Organization.slug == ORG_SLUG))
    if org is None:
        org = Organization(
            name=ORG_NAME,
            slug=ORG_SLUG,
            kind="platform",
            created_by=user.id,
        )
        db.add(org)
        db.flush()
    existing = db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == org.id,
        )
    )
    if existing is None:
        db.add(
            Membership(
                user_id=user.id,
                organization_id=org.id,
                role_code="super_admin",
                created_by=user.id,
            )
        )
    db.commit()
    print(f"LOCAL Super Admin membership ready: {ORG_NAME} ({ORG_SLUG})")
    print("Hosted database untouched. Production RBAC unchanged.")


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Missing local DB {DB_PATH}. Run wave7_local_bootstrap.py first.")
    engine = create_engine(f"sqlite:///{DB_PATH}", future=True)
    with Session(engine) as db:
        ensure_local_super_admin(db)


if __name__ == "__main__":
    main()
