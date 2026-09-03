"""identity + work id core: account security, privacy, consent, verification

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-03

STRICTLY ADDITIVE and safe:
- ALTERs only tables created by the canonical foundation (0001) — none of
  these tables exist in the shared Supabase schema, so nothing live is
  touched. All new columns are nullable or have server defaults.
- Creates four brand-new tables (verification/reset tokens, consents,
  per-section visibility).
Rollback drops exactly the objects this revision created/added.

New tables: email_verification_tokens, password_reset_tokens,
            consents, person_visibility_settings
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
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
    # ---- Account security (users) ------------------------------------------
    op.add_column(
        "users", sa.Column("mfa_secret", sa.String(200), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="0"),
    )

    # ---- Person profile ----------------------------------------------------
    op.add_column("person_profiles", sa.Column("preferred_name", sa.String(120)))
    op.add_column("person_profiles", sa.Column("city", sa.String(120)))
    op.add_column("person_profiles", sa.Column("state_province", sa.String(120)))
    op.add_column("person_profiles", sa.Column("phone", sa.String(40)))

    # ---- Work ID sections --------------------------------------------------
    op.add_column("work_experiences", sa.Column("department", sa.String(160)))
    op.add_column("work_experiences", sa.Column("skills_used", sa.JSON()))
    op.add_column(
        "work_experiences",
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="unverified",
        ),
    )

    op.add_column("educations", sa.Column("level", sa.String(60)))
    op.add_column(
        "educations",
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="unverified",
        ),
    )

    op.add_column("employments", sa.Column("department", sa.String(160)))
    op.add_column("employments", sa.Column("location", sa.String(160)))
    op.add_column("employments", sa.Column("skills_used", sa.JSON()))
    op.add_column(
        "employments",
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="unverified",
        ),
    )

    # ---- Verification / reset tokens ---------------------------------------
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", tz, nullable=False),
        sa.Column("used_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens", ["user_id"],
    )
    op.create_index(
        "ix_email_verification_tokens_token_hash",
        "email_verification_tokens", ["token_hash"], unique=True,
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", tz, nullable=False),
        sa.Column("used_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"]
    )
    op.create_index(
        "ix_password_reset_tokens_token_hash",
        "password_reset_tokens", ["token_hash"], unique=True,
    )

    # ---- Consent -----------------------------------------------------------
    op.create_table(
        "consents",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "grantee_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE")
        ),
        sa.Column(
            "grantee_organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("resource_scope", sa.String(120), nullable=False),
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
    op.create_index("ix_consents_person_id", "consents", ["person_id"])
    op.create_index(
        "ix_consents_grantee_organization_id", "consents",
        ["grantee_organization_id"],
    )

    # ---- Per-section visibility --------------------------------------------
    op.create_table(
        "person_visibility_settings",
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("scope", sa.String(80), primary_key=True),
        sa.Column(
            "visibility", sa.String(20), nullable=False, server_default="private"
        ),
        sa.Column("updated_at", tz, server_default=now),
    )


def downgrade() -> None:
    op.drop_table("person_visibility_settings")
    op.drop_index("ix_consents_grantee_organization_id", table_name="consents")
    op.drop_index("ix_consents_person_id", table_name="consents")
    op.drop_table("consents")
    op.drop_index(
        "ix_password_reset_tokens_token_hash", table_name="password_reset_tokens"
    )
    op.drop_index(
        "ix_password_reset_tokens_user_id", table_name="password_reset_tokens"
    )
    op.drop_table("password_reset_tokens")
    op.drop_index(
        "ix_email_verification_tokens_token_hash",
        table_name="email_verification_tokens",
    )
    op.drop_index(
        "ix_email_verification_tokens_user_id",
        table_name="email_verification_tokens",
    )
    op.drop_table("email_verification_tokens")

    with op.batch_alter_table("employments") as batch:
        batch.drop_column("verification_status")
        batch.drop_column("skills_used")
        batch.drop_column("location")
        batch.drop_column("department")
    with op.batch_alter_table("educations") as batch:
        batch.drop_column("verification_status")
        batch.drop_column("level")
    with op.batch_alter_table("work_experiences") as batch:
        batch.drop_column("verification_status")
        batch.drop_column("skills_used")
        batch.drop_column("department")
    with op.batch_alter_table("person_profiles") as batch:
        batch.drop_column("phone")
        batch.drop_column("state_province")
        batch.drop_column("city")
        batch.drop_column("preferred_name")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("mfa_enabled")
        batch.drop_column("mfa_secret")
