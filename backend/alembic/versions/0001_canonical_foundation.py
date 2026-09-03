"""canonical foundation: identity, tenancy, RBAC, work id, documents, audit

Revision ID: 0001
Revises:
Create Date: 2026-09-03

STRICTLY ADDITIVE — creates only NEW tables (none of these exist in the
current Supabase careers/core schema). No existing table, column, index,
constraint, or RLS policy is touched. Rollback drops exactly the objects
this revision created; zero data-loss risk to pre-existing data.

Tables created:
  users, person_profiles, refresh_tokens,
  organizations, memberships, roles, permissions, role_permissions,
  work_experiences, educations, skills, user_skills, credentials, employments,
  person_documents, document_access_grants, audit_log
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
now = sa.text("CURRENT_TIMESTAMP")
tz = sa.DateTime(timezone=True)


def _timestamps() -> list:
    return [
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    ]


def upgrade() -> None:
    # ---- Identity ---------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("email_verified_at", tz),
        sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "person_profiles",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("headline", sa.String(200)),
        sa.Column("summary", sa.String(4000)),
        sa.Column("location", sa.String(160)),
        sa.Column("country_code", sa.String(8)),
        sa.Column("date_of_birth", tz),
        sa.Column("profile_photo_storage_key", sa.String(255)),
        *_timestamps(),
    )
    op.create_index("ix_person_profiles_user_id", "person_profiles", ["user_id"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", tz, nullable=False),
        sa.Column("revoked_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("ip_address", sa.String(64)),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # ---- Tenancy / RBAC ---------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="employer"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        *_timestamps(),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    op.create_table(
        "roles",
        sa.Column("code", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("description", sa.Text()),
    )
    op.create_table(
        "permissions",
        sa.Column("code", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text()),
    )
    op.create_table(
        "role_permissions",
        sa.Column(
            "role_code", sa.String(50),
            sa.ForeignKey("roles.code", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "permission_code", sa.String(100),
            sa.ForeignKey("permissions.code", ondelete="CASCADE"), primary_key=True,
        ),
    )
    op.create_table(
        "memberships",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "role_code", sa.String(50), sa.ForeignKey("roles.code"), nullable=False
        ),
        sa.Column(
            "created_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint(
            "user_id", "organization_id", name="uq_memberships_user_org"
        ),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index(
        "ix_memberships_organization_id", "memberships", ["organization_id"]
    )

    # ---- Work ID ----------------------------------------------------------
    op.create_table(
        "work_experiences",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("company_id", uuid_type),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("location", sa.String(160)),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text()),
        *_timestamps(),
    )
    op.create_index(
        "ix_work_experiences_person_id", "work_experiences", ["person_id"]
    )

    op.create_table(
        "educations",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("institution", sa.String(200), nullable=False),
        sa.Column("degree", sa.String(200)),
        sa.Column("field_of_study", sa.String(200)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_educations_person_id", "educations", ["person_id"])

    op.create_table(
        "skills",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(60), nullable=False, server_default="general"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_skills_name", "skills", ["name"], unique=True)

    op.create_table(
        "user_skills",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "skill_id", uuid_type, sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("level", sa.String(20), nullable=False, server_default="intermediate"),
        sa.Column("years_experience", sa.Float()),
        sa.UniqueConstraint(
            "person_id", "skill_id", name="uq_user_skills_person_skill"
        ),
        *_timestamps(),
    )
    op.create_index("ix_user_skills_person_id", "user_skills", ["person_id"])

    op.create_table(
        "credentials",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("issuer", sa.String(200)),
        sa.Column("credential_type", sa.String(32), nullable=False,
                  server_default="certification"),
        sa.Column("credential_number", sa.String(120)),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="unverified"),
        sa.Column("issued_at", sa.Date()),
        sa.Column("expires_at", sa.Date()),
        sa.Column("verified_at", tz),
        sa.Column("verification_source", sa.String(200)),
        sa.Column("document_id", uuid_type),
        *_timestamps(),
    )
    op.create_index("ix_credentials_person_id", "credentials", ["person_id"])

    op.create_table(
        "employments",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("company_name", sa.String(200), nullable=False),
        sa.Column("company_id", uuid_type),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("employment_type", sa.String(32), nullable=False,
                  server_default="full_time"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="0"),
        *_timestamps(),
    )
    op.create_index("ix_employments_person_id", "employments", ["person_id"])

    # ---- Documents --------------------------------------------------------
    op.create_table(
        "person_documents",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("doc_type", sa.String(60), nullable=False),
        sa.Column("storage_key", sa.String(255)),
        sa.Column("mime_type", sa.String(100)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("verification_status", sa.String(20), nullable=False,
                  server_default="unverified"),
        *_timestamps(),
    )
    op.create_index("ix_person_documents_person_id", "person_documents", ["person_id"])

    op.create_table(
        "document_access_grants",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "document_id", uuid_type,
            sa.ForeignKey("person_documents.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "grantee_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE")
        ),
        sa.Column(
            "grantee_organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("purpose", sa.String(240)),
        sa.Column(
            "granted_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("granted_at", tz, server_default=now, nullable=False),
        sa.Column("expires_at", tz),
        sa.Column("revoked_at", tz),
        sa.Column(
            "revoked_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
    )
    op.create_index(
        "ix_document_access_grants_document_id",
        "document_access_grants",
        ["document_id"],
    )

    # ---- Audit ------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "actor_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(80)),
        sa.Column("resource_id", sa.String(64)),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column("result", sa.String(20), nullable=False, server_default="success"),
        sa.Column("request_id", sa.String(40)),
        sa.Column("ip_address", sa.String(64)),
        sa.Column("user_agent", sa.String(255)),
        sa.Column("payload", sa.JSON()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"])
    op.create_index(
        "ix_audit_log_actor_created", "audit_log", ["actor_id", "created_at"]
    )
    op.create_index(
        "ix_audit_log_action_created", "audit_log", ["action", "created_at"]
    )
    op.create_index(
        "ix_audit_log_resource", "audit_log", ["resource_type", "resource_id"]
    )

    # ---- Seed: role/permission catalog ------------------------------------
    _seed_catalog()


def _seed_catalog() -> None:
    roles = sa.table(
        "roles",
        sa.column("code", sa.String(50)),
        sa.column("name", sa.String(120)),
        sa.column("scope", sa.String(20)),
        sa.column("description", sa.Text()),
    )
    op.bulk_insert(
        roles,
        [
            {"code": "super_admin", "name": "Super Admin",
             "scope": "platform", "description": "Platform-wide administration."},
            {"code": "customer_support", "name": "Customer Support",
             "scope": "platform", "description": "Companies, plans, tickets."},
            {"code": "tech_support", "name": "Tech Support",
             "scope": "platform", "description": "Auth diagnostics, sessions, MFA."},
            {"code": "marketing", "name": "Marketing",
             "scope": "platform", "description": "Campaigns and audiences."},
            {"code": "finance", "name": "Finance",
             "scope": "platform", "description": "Billing, invoices, payments."},
            {"code": "org_admin", "name": "Organization Admin",
             "scope": "organization", "description": "Org settings, members, jobs."},
            {"code": "hr", "name": "HR",
             "scope": "organization", "description": "Jobs, applications, offers."},
            {"code": "recruiter", "name": "Recruiter",
             "scope": "organization", "description": "Candidate discovery."},
            {"code": "hiring_manager", "name": "Hiring Manager",
             "scope": "organization", "description": "Review applications."},
            {"code": "government_admin", "name": "Government Admin",
             "scope": "government", "description": "Authorized gov scopes."},
            {"code": "government_user", "name": "Government Analyst",
             "scope": "government", "description": "Aggregate workforce data."},
        ],
    )

    permissions = sa.table(
        "permissions",
        sa.column("code", sa.String(100)),
        sa.column("name", sa.String(160)),
        sa.column("description", sa.Text()),
    )
    op.bulk_insert(
        permissions,
        [
            {"code": "users.read", "name": "Read user records"},
            {"code": "users.update", "name": "Update user records"},
            {"code": "orgs.read", "name": "Read organization records"},
            {"code": "orgs.update", "name": "Update organization records"},
            {"code": "members.read", "name": "Read organization members"},
            {"code": "members.manage", "name": "Manage organization members"},
            {"code": "jobs.create", "name": "Create jobs"},
            {"code": "jobs.read", "name": "Read jobs"},
            {"code": "jobs.update", "name": "Update jobs"},
            {"code": "candidates.read", "name": "Read candidate data"},
            {"code": "candidates.update", "name": "Update candidate data"},
            {"code": "interviews.create", "name": "Create interviews"},
            {"code": "interviews.read", "name": "Read interviews"},
            {"code": "billing.read", "name": "Read billing data"},
            {"code": "billing.manage", "name": "Manage billing"},
            {"code": "support.read", "name": "Read support data"},
            {"code": "marketing.manage", "name": "Manage marketing"},
            {"code": "audit.read", "name": "Read audit logs"},
            {"code": "sessions.manage", "name": "Manage user sessions"},
            {"code": "workforce.aggregates.read",
             "name": "Read aggregated workforce intelligence"},
            {"code": "admin.manage", "name": "Platform administration"},
        ],
    )

    # Maps seeded in code (app.models.catalog.ROLE_PERMISSIONS); keep in sync.
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String(50)),
        sa.column("permission_code", sa.String(100)),
    )
    role_permission_rows = [
        ("customer_support", "users.read"), ("customer_support", "orgs.read"),
        ("customer_support", "support.read"), ("customer_support", "billing.read"),
        ("tech_support", "users.read"), ("tech_support", "users.update"),
        ("tech_support", "sessions.manage"), ("tech_support", "audit.read"),
        ("marketing", "marketing.manage"),
        ("finance", "billing.read"), ("finance", "billing.manage"),
        ("finance", "audit.read"),
        ("org_admin", "orgs.read"), ("org_admin", "orgs.update"),
        ("org_admin", "members.read"), ("org_admin", "members.manage"),
        ("org_admin", "jobs.create"), ("org_admin", "jobs.read"),
        ("org_admin", "jobs.update"), ("org_admin", "candidates.read"),
        ("org_admin", "candidates.update"), ("org_admin", "interviews.create"),
        ("org_admin", "interviews.read"), ("org_admin", "billing.read"),
        ("hr", "orgs.read"), ("hr", "jobs.create"), ("hr", "jobs.read"),
        ("hr", "jobs.update"), ("hr", "candidates.read"),
        ("hr", "candidates.update"), ("hr", "interviews.create"),
        ("hr", "interviews.read"),
        ("recruiter", "orgs.read"), ("recruiter", "jobs.read"),
        ("recruiter", "candidates.read"),
        ("hiring_manager", "orgs.read"), ("hiring_manager", "jobs.read"),
        ("hiring_manager", "candidates.read"),
        ("hiring_manager", "interviews.create"),
        ("hiring_manager", "interviews.read"),
        ("government_admin", "orgs.read"),
        ("government_admin", "workforce.aggregates.read"),
        ("government_user", "workforce.aggregates.read"),
    ]
    op.bulk_insert(
        role_permissions,
        [{"role_code": r, "permission_code": p} for r, p in role_permission_rows],
    )
    # super_admin implicitly holds every permission (enforced in app code).


def downgrade() -> None:
    # Drop exactly what upgrade created, newest first.
    op.drop_index("ix_audit_log_resource", table_name="audit_log")
    op.drop_index("ix_audit_log_action_created", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_created", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index(
        "ix_document_access_grants_document_id", table_name="document_access_grants"
    )
    op.drop_table("document_access_grants")
    op.drop_index("ix_person_documents_person_id", table_name="person_documents")
    op.drop_table("person_documents")

    op.drop_index("ix_employments_person_id", table_name="employments")
    op.drop_table("employments")
    op.drop_index("ix_credentials_person_id", table_name="credentials")
    op.drop_table("credentials")
    op.drop_index("ix_user_skills_person_id", table_name="user_skills")
    op.drop_table("user_skills")
    op.drop_index("ix_skills_name", table_name="skills")
    op.drop_table("skills")
    op.drop_index("ix_educations_person_id", table_name="educations")
    op.drop_table("educations")
    op.drop_index("ix_work_experiences_person_id", table_name="work_experiences")
    op.drop_table("work_experiences")

    op.drop_index("ix_memberships_organization_id", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")

    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_person_profiles_user_id", table_name="person_profiles")
    op.drop_table("person_profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
