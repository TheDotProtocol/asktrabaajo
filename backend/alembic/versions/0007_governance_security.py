"""platform governance: reports, events, rate-limit hits, notification prefs

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-03

STRICTLY ADDITIVE and safe:
- Creates five brand-new canonical tables for the Phase 9 governance /
  realtime / rate-limiting / notification layers (none of these names exist
  in the live Supabase careers schema — nothing legacy is touched).
- Seeds the platform-scoped ``moderator`` and ``governance_auditor`` roles
  plus Phase 9 permissions and role mappings (idempotent by PK).
Rollback drops exactly what this revision created.

New tables: governance_reports, governance_report_notes, platform_events,
            rate_limit_hits, notification_preferences
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
now = sa.text("CURRENT_TIMESTAMP")
tz = sa.DateTime(timezone=True)

NEW_ROLES = [
    ("moderator", "Governance Moderator", "platform",
     "Platform governance: report queue, notes, assignments, resolutions."),
    ("governance_auditor", "Governance Auditor", "platform",
     "Read-only governance + platform audit review."),
]
NEW_PERMISSIONS = [
    ("reports.read", "Read the platform governance report queue"),
    ("reports.manage", "Manage reports (status, internal notes)"),
    ("reports.assign", "Assign reports to moderators"),
    ("reports.resolve", "Resolve and reopen reports"),
    ("reports.audit", "Read governance audit history"),
    ("moderation.read", "Read moderation data"),
    ("moderation.manage", "Manage moderation data"),
    ("platform.audit.read", "Read platform-wide audit records"),
]
ROLE_ADDITIONS = {
    "moderator": [
        "users.read", "orgs.read",
        "reports.read", "reports.manage", "reports.assign", "reports.resolve",
        "reports.audit", "moderation.read", "platform.audit.read",
    ],
    "governance_auditor": [
        "reports.read", "reports.audit", "moderation.read", "platform.audit.read",
    ],
}


def upgrade() -> None:
    conn = op.get_bind()

    # ---- governance_reports ----------------------------------------------------
    op.create_table(
        "governance_reports",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "reporter_user_id", uuid_type, sa.ForeignKey("users.id",
                                                         ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=False),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column("category", sa.String(40), nullable=False,
                  server_default="other"),
        sa.Column("severity", sa.String(16), nullable=False,
                  server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("evidence_refs", sa.JSON()),
        sa.Column(
            "assigned_moderator_id", uuid_type,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("resolution", sa.Text()),
        sa.Column("resolved_at", tz),
        sa.Column(
            "resolved_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("reopened_count", sa.Integer(), nullable=False,
                  server_default="0"),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_governance_reports_status_severity", "governance_reports",
        ["status", "severity"],
    )
    op.create_index(
        "ix_governance_reports_target", "governance_reports", ["target_type",
                                                               "target_id"]
    )
    op.create_index(
        "ix_governance_reports_organization_id", "governance_reports",
        ["organization_id"],
    )
    op.create_index(
        "ix_governance_reports_assigned_moderator_id", "governance_reports",
        ["assigned_moderator_id"],
    )

    # ---- governance_report_notes -----------------------------------------------
    op.create_table(
        "governance_report_notes",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "report_id", uuid_type, sa.ForeignKey("governance_reports.id",
                                                  ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_user_id", uuid_type, sa.ForeignKey("users.id",
                                                       ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_governance_report_notes_report_id", "governance_report_notes",
        ["report_id"],
    )

    # ---- platform_events --------------------------------------------------------
    op.create_table(
        "platform_events",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column(
            "recipient_user_id", uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("org_scope", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column(
            "actor_user_id", uuid_type, sa.ForeignKey("users.id",
                                                      ondelete="SET NULL")
        ),
        sa.Column("payload", sa.JSON()),
        sa.Column("read_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_platform_events_recipient_created", "platform_events",
        ["recipient_user_id", "created_at"],
    )
    op.create_index(
        "ix_platform_events_org_created", "platform_events",
        ["organization_id", "created_at"],
    )
    op.create_index("ix_platform_events_recipient_user_id", "platform_events",
                    ["recipient_user_id"])
    op.create_index("ix_platform_events_organization_id", "platform_events",
                    ["organization_id"])

    # ---- rate_limit_hits ---------------------------------------------------------
    op.create_table(
        "rate_limit_hits",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("scope", sa.String(60), nullable=False),
        sa.Column("key", sa.String(160), nullable=False),
        sa.Column("hit_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_rate_limit_hits_scope_key_hit", "rate_limit_hits",
        ["scope", "key", "hit_at"],
    )

    # ---- notification_preferences --------------------------------------------------
    op.create_table(
        "notification_preferences",
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("channel", sa.String(20), primary_key=True,
                  server_default="in_app"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )

    # ---- RBAC seeds -------------------------------------------------------------
    roles_table = sa.table(
        "roles",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("scope", sa.String),
        sa.column("description", sa.Text),
    )
    for code, name, scope, description in NEW_ROLES:
        exists = conn.execute(
            sa.select(sa.literal(1)).select_from(roles_table).where(
                roles_table.c.code == code
            )
        ).first()
        if exists is None:
            conn.execute(
                roles_table.insert().values(
                    code=code, name=name, scope=scope, description=description
                )
            )

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
            conn.execute(permissions_table.insert().values(code=code, name=name))

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
    roles_table = sa.table(
        "roles",
        sa.column("code", sa.String),
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
    for code, _name, _scope, _desc in NEW_ROLES:
        conn.execute(roles_table.delete().where(roles_table.c.code == code))

    op.drop_table("notification_preferences")
    op.drop_index("ix_rate_limit_hits_scope_key_hit", table_name="rate_limit_hits")
    op.drop_table("rate_limit_hits")
    op.drop_index("ix_platform_events_organization_id", table_name="platform_events")
    op.drop_index("ix_platform_events_recipient_user_id", table_name="platform_events")
    op.drop_index(
        "ix_platform_events_org_created", table_name="platform_events"
    )
    op.drop_index(
        "ix_platform_events_recipient_created", table_name="platform_events"
    )
    op.drop_table("platform_events")
    op.drop_index(
        "ix_governance_report_notes_report_id", table_name="governance_report_notes"
    )
    op.drop_table("governance_report_notes")
    op.drop_index(
        "ix_governance_reports_assigned_moderator_id", table_name="governance_reports"
    )
    op.drop_index(
        "ix_governance_reports_organization_id", table_name="governance_reports"
    )
    op.drop_index(
        "ix_governance_reports_target", table_name="governance_reports"
    )
    op.drop_index(
        "ix_governance_reports_status_severity", table_name="governance_reports"
    )
    op.drop_table("governance_reports")