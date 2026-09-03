"""company employment os: profiles, job postings, scorecards, doc requests

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-03

STRICTLY ADDITIVE and safe:
- Adds a nullable ``job_id`` column to canonical ``job_applications`` (a
  denormalized employer-pipeline link; existing rows unaffected).
- Creates five brand-new canonical tables: company_profiles, job_postings,
  screening_responses, interview_scorecards, document_requests.
- Inserts the Phase 6 employer permissions + role->permission mappings into
  the canonical RBAC catalog (idempotent by primary key).
None of these names exist in the live Supabase careers schema, so nothing
legacy is touched. Rollback drops exactly what this revision created.

New tables: company_profiles, job_postings, screening_responses,
            interview_scorecards, document_requests
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
now = sa.text("CURRENT_TIMESTAMP")
tz = sa.DateTime(timezone=True)

# Employer permissions added by Phase 6 (mapped in models/catalog.py).
NEW_PERMISSIONS = [
    ("jobs.view", "View own organization's jobs"),
    ("jobs.publish", "Publish / pause / close jobs"),
    ("candidates.view", "View candidates in the organization's pipeline"),
    ("applications.view", "View the organization's applications"),
    ("applications.manage", "Advance / hold / reject applications"),
    ("interviews.manage", "Manage interviews + feedback"),
    ("offers.create", "Create offers"),
    ("offers.manage", "Manage offers"),
    ("analytics.view", "View organization hiring analytics"),
    ("company.manage", "Manage the company profile"),
]

# role -> new permission codes
ROLE_ADDITIONS = {
    "org_admin": [
        "company.manage", "jobs.view", "jobs.publish", "candidates.view",
        "applications.view", "applications.manage", "interviews.manage",
        "offers.create", "offers.manage", "analytics.view",
    ],
    "hr": [
        "jobs.view", "jobs.publish", "candidates.view",
        "applications.view", "applications.manage", "interviews.manage",
        "offers.create", "offers.manage", "analytics.view",
    ],
    "recruiter": [
        "jobs.view", "candidates.view", "applications.view",
        "applications.manage", "interviews.manage",
    ],
    "hiring_manager": [
        "jobs.view", "candidates.view", "applications.view", "interviews.manage",
    ],
}


def upgrade() -> None:
    # ---- job_applications: employer-pipeline link ----------------------------
    op.add_column("job_applications", sa.Column("job_id", uuid_type))

    # ---- Company profile (1:1 with organizations) ----------------------------
    op.create_table(
        "company_profiles",
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column("legal_name", sa.String(240)),
        sa.Column("display_name", sa.String(240)),
        sa.Column("industry", sa.String(120)),
        sa.Column("sector", sa.String(120)),
        sa.Column("country", sa.String(80)),
        sa.Column("city", sa.String(120)),
        sa.Column("website_url", sa.String(300)),
        sa.Column("company_size", sa.String(40)),
        sa.Column("company_type", sa.String(40)),
        sa.Column("description", sa.Text()),
        sa.Column("contact_name", sa.String(160)),
        sa.Column("contact_email", sa.String(320)),
        sa.Column(
            "verification_status", sa.String(20),
            nullable=False, server_default="unverified",
        ),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )

    # ---- Job postings ---------------------------------------------------------
    op.create_table(
        "job_postings",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "opportunity_id", uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("department", sa.String(160)),
        sa.Column("summary", sa.Text()),
        sa.Column("description", sa.Text()),
        sa.Column("responsibilities", sa.JSON()),
        sa.Column("requirements", sa.JSON()),
        sa.Column("skills_required", sa.JSON()),
        sa.Column("preferred_skills", sa.JSON()),
        sa.Column("experience_level", sa.String(80)),
        sa.Column("education_level", sa.String(60)),
        sa.Column("location", sa.String(200)),
        sa.Column("country", sa.String(80)),
        sa.Column("city", sa.String(120)),
        sa.Column("remote_eligible", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("work_mode", sa.String(20)),
        sa.Column("employment_type", sa.String(32)),
        sa.Column("salary_min", sa.Float()),
        sa.Column("salary_max", sa.Float()),
        sa.Column("salary_currency", sa.String(8), server_default="USD"),
        sa.Column("seniority", sa.String(40)),
        sa.Column("industry", sa.String(120)),
        sa.Column("languages", sa.JSON()),
        sa.Column("openings_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("application_deadline", sa.Date()),
        sa.Column("screening_questions", sa.JSON()),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", tz),
        sa.Column("closed_at", tz),
        sa.Column("imported_from", sa.String(120)),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint("organization_id", "slug", name="uq_job_postings_org_slug"),
    )
    op.create_index("ix_job_postings_organization_id", "job_postings", ["organization_id"])
    op.create_index("ix_job_postings_opportunity_id", "job_postings", ["opportunity_id"])
    op.create_index("ix_job_postings_status", "job_postings", ["status"])

    # ---- Screening responses ---------------------------------------------------
    op.create_table(
        "screening_responses",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "application_id", uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "job_id", uuid_type,
            sa.ForeignKey("job_postings.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("answers", sa.JSON()),
        sa.Column("submitted_at", tz, server_default=now, nullable=False),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_screening_responses_application_id", "screening_responses",
        ["application_id"],
    )

    # ---- Interview scorecards ----------------------------------------------------
    op.create_table(
        "interview_scorecards",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "interview_id", uuid_type,
            sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "interviewer_user_id", uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("criteria", sa.JSON()),
        sa.Column("strengths", sa.Text()),
        sa.Column("concerns", sa.Text()),
        sa.Column("recommendation", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_interview_scorecards_interview_id", "interview_scorecards", ["interview_id"]
    )

    # ---- Document requests ---------------------------------------------------------
    op.create_table(
        "document_requests",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "application_id", uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "requested_by", uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("document_type", sa.String(60), nullable=False),
        sa.Column("purpose", sa.String(240)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("responded_at", tz),
        sa.Column("responded_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_document_requests_application_id", "document_requests", ["application_id"])
    op.create_index("ix_document_requests_organization_id", "document_requests", ["organization_id"])

    # ---- RBAC catalog: employer permissions ---------------------------------------
    conn = op.get_bind()
    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
    )
    for code, name in NEW_PERMISSIONS:
        exists = conn.execute(
            sa.select(sa.literal(1)).select_from(permissions_table).where(
                permissions_table.c.code == code
            )
        ).first()
        if exists is None:
            conn.execute(
                permissions_table.insert().values(code=code, name=name)
            )

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    for role_code, codes in ROLE_ADDITIONS.items():
        for permission_code in codes:
            exists = conn.execute(
                sa.select(sa.literal(1)).select_from(role_permissions).where(
                    role_permissions.c.role_code == role_code,
                    role_permissions.c.permission_code == permission_code,
                )
            ).first()
            if exists is None:
                conn.execute(
                    role_permissions.insert().values(
                        role_code=role_code, permission_code=permission_code
                    )
                )


def downgrade() -> None:
    conn = op.get_bind()
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String),
    )
    for role_code, codes in ROLE_ADDITIONS.items():
        for permission_code in codes:
            conn.execute(
                role_permissions.delete().where(
                    role_permissions.c.role_code == role_code,
                    role_permissions.c.permission_code == permission_code,
                )
            )
    for code, _name in NEW_PERMISSIONS:
        conn.execute(permissions_table.delete().where(permissions_table.c.code == code))

    op.drop_index("ix_document_requests_organization_id", table_name="document_requests")
    op.drop_index("ix_document_requests_application_id", table_name="document_requests")
    op.drop_table("document_requests")
    op.drop_index("ix_interview_scorecards_interview_id", table_name="interview_scorecards")
    op.drop_table("interview_scorecards")
    op.drop_index(
        "ix_screening_responses_application_id", table_name="screening_responses"
    )
    op.drop_table("screening_responses")
    op.drop_table("job_postings")
    op.drop_table("company_profiles")
    op.drop_column("job_applications", "job_id")
