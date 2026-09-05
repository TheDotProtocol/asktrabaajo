"""Wave 7 — isolated local SQLite bootstrap.

Recreates backend/asktrabaajo_wave6.db (same file the local API uses) with
Wave 6 DEV users plus the Wave 7 multi-portal identity. Never reads or writes
hosted Supabase.

Password for the Wave 7 account is read from WAVE7_DEV_PASSWORD or the
gitignored file backend/.wave7-dev-account. It is never committed.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
DB_PATH = BACKEND / "asktrabaajo_wave6.db"
CREDS_PATH = BACKEND / ".wave7-dev-account"
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
from app.models.company import CompanyProfile  # noqa: E402
from app.models.career import CareerGoal  # noqa: E402
from app.models.governance import GOVERNANCE_TEAM_SEEDS, GovernanceTeam  # noqa: E402
from app.models.work import Credential, Education, WorkExperience  # noqa: E402
from app.services.auth_service import get_person_for_user, register_user  # noqa: E402
from app.services import company_os, skills_registry, tenancy  # noqa: E402

WAVE6_PASSWORD = "Wave6-dev-local!"
WAVE6_USERS = (
    ("dev+wave6.candidate@example.com", "DEV Wave6 Candidate", None),
    ("dev+wave6.employer@example.com", "DEV Wave6 Employer", "employer"),
    ("dev+wave6.admin@example.com", "DEV Wave6 Admin", "admin"),
)

WAVE7_EMAIL = "akumartrabaajo@gmail.com"
WAVE7_NAME = "AskTrabaajo DEV Inspector"


def read_wave7_password() -> str:
    env = os.environ.get("WAVE7_DEV_PASSWORD")
    if env:
        return env
    if CREDS_PATH.exists():
        for line in CREDS_PATH.read_text().splitlines():
            if line.startswith("password="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value
    raise SystemExit(
        "Wave 7 password missing. Set WAVE7_DEV_PASSWORD or create "
        f"{CREDS_PATH} (gitignored)."
    )


def write_creds_file(password: str) -> None:
    CREDS_PATH.write_text(
        "\n".join(
            [
                "# LOCAL DEVELOPMENT ONLY — do not commit",
                f"email={WAVE7_EMAIL}",
                f"password={password}",
                "",
            ]
        )
    )


def seed_wave7_identity(db: Session, user: User) -> None:
    person = get_person_for_user(db, user.id)
    assert person is not None
    person.headline = "DEV inspector — not a real professional identity"
    person.summary = (
        "Development fixture for local visual QA. This Work ID is labelled DEV "
        "and must not be treated as a production person."
    )
    person.preferred_name = "DEV Inspector"
    person.city = "Development City"
    person.country_code = "DEV"

    db.add(
        WorkExperience(
            person_id=person.id,
            company_name="AskTrabaajo DEV Company",
            title="DEV Product Inspector",
            location="Development",
            start_date=date(2024, 1, 1),
            is_current=True,
            description="DEV work-history placeholder. Not a real employment record.",
        )
    )
    db.add(
        Education(
            person_id=person.id,
            institution="AskTrabaajo DEV Academy",
            level="bachelor",
            degree="DEV placeholder",
            field_of_study="Product inspection",
            start_date=date(2018, 9, 1),
            end_date=date(2022, 6, 1),
        )
    )
    db.add(
        Credential(
            person_id=person.id,
            name="DEV visual QA credential",
            issuer="AskTrabaajo Development",
        )
    )
    db.add(
        CareerGoal(
            person_id=person.id,
            title="Inspect AskTrabaajo portals",
            target_role="DEV inspector",
            is_primary=True,
        )
    )
    db.flush()
    for name, level, years in (
        ("Python", "advanced", 4),
        ("React", "intermediate", 3),
        ("SQL", "intermediate", 2),
    ):
        skill = skills_registry.ensure_skill(db, name)
        from app.models.work import UserSkill

        db.add(
            UserSkill(
                person_id=person.id,
                skill_id=skill.id,
                level=level,
                years_experience=years,
            )
        )


def seed_wave8_workforce(db: Session, inspector: User, employer_org: Organization) -> None:
    """Deterministic DEV cohorts for k-threshold inspection.

    Development City + Python: large enough to display.
    Sparse Town + RareSkillDEV: below the default threshold (suppressed).
    """
    profile = db.scalar(
        select(CompanyProfile).where(CompanyProfile.organization_id == employer_org.id)
    )
    if profile is None:
        profile = CompanyProfile(
            organization_id=employer_org.id,
            display_name="AskTrabaajo DEV Company",
            industry="Technology",
            country="DEV",
            city="Development City",
        )
        db.add(profile)
    else:
        profile.industry = profile.industry or "Technology"
        profile.country = profile.country or "DEV"
        profile.city = profile.city or "Development City"

    extra = company_os.create_job(
        db,
        employer_org.id,
        inspector.id,
        title="DEV Python Role",
        summary="DEV fixture for skill demand. Not a real opening.",
        description="Marked DEV.",
        skills_required=["Python"],
        industry="Technology",
        location="Development",
        city="Development City",
        country="DEV",
        remote_eligible=True,
        employment_type="full_time",
    )
    company_os.publish_job(db, employer_org.id, extra.id)

    for index in range(1, 12):
        email = f"dev+gov.wf.{index:02d}@example.com"
        register_user(db, email=email, password=WAVE6_PASSWORD, full_name=f"DEV Workforce {index:02d}")
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        person = get_person_for_user(db, user.id)
        assert person is not None
        person.city = "Development City"
        person.country_code = "DEV"
        person.headline = "DEV workforce fixture"
        skill = skills_registry.ensure_skill(db, "Python")
        from app.models.work import UserSkill

        db.add(
            UserSkill(
                person_id=person.id,
                skill_id=skill.id,
                level="intermediate",
                years_experience=2,
            )
        )
        db.add(
            WorkExperience(
                person_id=person.id,
                company_name="AskTrabaajo DEV Company",
                title="DEV Worker",
                location="Development",
                start_date=date(2024, 1, 1),
                is_current=True,
                description="DEV fixture. Not a real employment record.",
            )
        )

    for index in range(1, 4):
        email = f"dev+gov.sparse.{index:02d}@example.com"
        register_user(db, email=email, password=WAVE6_PASSWORD, full_name=f"DEV Sparse {index:02d}")
        user = db.scalar(select(User).where(User.email == email))
        assert user is not None
        person = get_person_for_user(db, user.id)
        assert person is not None
        person.city = "Sparse Town"
        person.country_code = "DEV"
        person.headline = "DEV small-cohort fixture"
        skill = skills_registry.ensure_skill(db, "RareSkillDEV")
        from app.models.work import UserSkill

        db.add(
            UserSkill(
                person_id=person.id,
                skill_id=skill.id,
                level="beginner",
                years_experience=1,
            )
        )
    db.commit()


def main() -> None:
    password = read_wave7_password()
    write_creds_file(password)

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

        for email, name, kind in WAVE6_USERS:
            register_user(db, email=email, password=WAVE6_PASSWORD, full_name=name)
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None
            if kind == "employer":
                org = Organization(name="DEV_WAVE6_ORG", slug="dev-wave6-org", kind="employer")
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

        register_user(db, email=WAVE7_EMAIL, password=password, full_name=WAVE7_NAME)
        inspector = db.scalar(select(User).where(User.email == WAVE7_EMAIL))
        assert inspector is not None
        seed_wave7_identity(db, inspector)
        db.commit()

        employer_org = tenancy.create_organization(
            db,
            actor_id=inspector.id,
            name="AskTrabaajo DEV Company",
            slug="asktrabaajo-dev-company",
            kind="employer",
        )
        job = company_os.create_job(
            db,
            employer_org.id,
            inspector.id,
            title="DEV Inspector Role",
            summary="Development job fixture. Not a real opening.",
            description="Marked DEV. Used only so the Employer Jobs screen has one row.",
            location="Development",
            city="Development City",
            country="DEV",
            remote_eligible=True,
            employment_type="full_time",
        )
        company_os.publish_job(db, employer_org.id, job.id)

        seed_wave8_workforce(db, inspector, employer_org)

        gov = Organization(
            name="AskTrabaajo DEV Government",
            slug="asktrabaajo-dev-government",
            kind="government",
            created_by=inspector.id,
        )
        db.add(gov)
        db.flush()
        db.add(
            Membership(
                user_id=inspector.id,
                organization_id=gov.id,
                role_code="government_user",
                created_by=inspector.id,
            )
        )
        platform = Organization(
            name="AskTrabaajo DEV Platform",
            slug="asktrabaajo-dev-platform",
            kind="platform",
            created_by=inspector.id,
        )
        db.add(platform)
        db.flush()
        db.add(
            Membership(
                user_id=inspector.id,
                organization_id=platform.id,
                role_code="super_admin",
                created_by=inspector.id,
            )
        )
        db.commit()

    print(f"WAVE7 LOCAL DB: {DB_PATH}")
    print(f"Wave 7 DEV email: {WAVE7_EMAIL}")
    print(f"Wave 7 password written to gitignored {CREDS_PATH}")
    print("Wave 6 accounts unchanged (candidate / employer / admin).")
    print("Memberships: jobseeker + employer org_admin + government_user + local super_admin.")
    print("Local Super Admin only. Hosted database untouched.")


if __name__ == "__main__":
    main()
