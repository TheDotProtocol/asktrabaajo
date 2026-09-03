"""0008 — Governance operations: teams, case links, priority + deterministic SLA.

Strictly additive (Phase 10):

- ``governance_teams``       — lightweight operational teams (seeded slugs).
- ``governance_team_members``— governance users in one or more teams.
- ``governance_case_links``  — link multiple reports into one investigation.
- ``governance_reports``     — new operational columns: priority, team_id,
  escalation markers, first-response time, and deterministic SLA deadline
  columns (response + resolution), computed from the priority policy.

RBAC: adds ``reports.escalate`` and ``reports.teams`` for moderator /
super_admin. Nothing is dropped; no data is rewritten. Validated locally only.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

UUID = sa.Uuid()  # cross-dialect (SQLite + Postgres) like migrations 0005-0007
tz = sa.DateTime(timezone=True)
now = sa.text("CURRENT_TIMESTAMP")

# Team slugs seeded for production parity with the model catalog.
TEAMS = [
    ("platform_safety", "Platform Safety", "Safety, harassment and abuse reports."),
    ("fraud", "Fraud", "Fraudulent jobs, offers and impersonation."),
    ("employer_integrity", "Employer Integrity", "Employer behaviour and policy reports."),
    ("candidate_integrity", "Candidate Integrity", "Candidate-side integrity reports."),
    ("communications", "Communications", "Communication disputes and outreach conduct."),
    ("document_trust", "Document Trust", "Document misuse and verification trust."),
    ("technical_abuse", "Technical Abuse", "Scraping, rate abuse and technical misuse."),
    ("general_support", "General Support", "Everything else routed for triage."),
]

NEW_PERMISSIONS = [
    ("reports.escalate", "Escalate cases and change priority/severity"),
    ("reports.teams", "Manage governance teams and their members"),
]

ROLE_ADDITIONS = {
    "moderator": ["reports.escalate", "reports.teams"],
    "super_admin": ["reports.escalate", "reports.teams"],
}


def upgrade() -> None:
    # ---- governance teams + members -----------------------------------------
    op.create_table(
        "governance_teams",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("slug", sa.String(40), unique=True, nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_table(
        "governance_team_members",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "team_id", UUID,
            sa.ForeignKey("governance_teams.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id", UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by", UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "uq_governance_team_members", "governance_team_members",
        ["team_id", "user_id"], unique=True,
    )

    # ---- case links ----------------------------------------------------------
    op.create_table(
        "governance_case_links",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "case_id", UUID,
            sa.ForeignKey("governance_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "linked_report_id", UUID,
            sa.ForeignKey("governance_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by", UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(300)),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "uq_governance_case_links", "governance_case_links",
        ["case_id", "linked_report_id"], unique=True,
    )
    op.create_index(
        "ix_governance_case_links_case", "governance_case_links", ["case_id"],
    )

    # ---- report operational columns -------------------------------------------
    # Batch mode: SQLite cannot ALTER with constraints; native ALTER on PG.
    with op.batch_alter_table("governance_reports") as batch:
        batch.add_column(
            sa.Column("priority", sa.String(16), nullable=False, server_default="normal")
        )
        batch.add_column(
            sa.Column(
                "team_id", UUID,
                sa.ForeignKey("governance_teams.id", ondelete="SET NULL"),
            )
        )
        batch.add_column(sa.Column("escalated_at", tz))
        batch.add_column(
            sa.Column(
                "escalated_to_team_id", UUID,
                sa.ForeignKey("governance_teams.id", ondelete="SET NULL"),
            )
        )
        batch.add_column(
            sa.Column("escalated_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL"))
        )
        batch.add_column(sa.Column("first_responded_at", tz))
        batch.add_column(sa.Column("sla_response_due_at", tz))
        batch.add_column(sa.Column("sla_resolution_due_at", tz))
        batch.create_index("ix_governance_reports_priority", ["priority", "status"])
        batch.create_index(
            "ix_governance_reports_sla_due", ["sla_resolution_due_at", "status"]
        )
        batch.create_index("ix_governance_reports_team", ["team_id"])

    # ---- seeds ----------------------------------------------------------------
    conn = op.get_bind()
    teams_table = sa.table(
        "governance_teams",
        sa.column("id", UUID),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
    )
    import uuid as _uuid

    for slug, name, description in TEAMS:
        exists = conn.execute(
            sa.select(sa.literal(1)).select_from(teams_table).where(
                teams_table.c.slug == slug
            )
        ).first()
        if exists is None:
            conn.execute(
                teams_table.insert().values(
                    id=_uuid.uuid4(), slug=slug, name=name, description=description
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
    # RBAC seeds: remove only what this revision added.
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
    for code in ["reports.escalate", "reports.teams"]:
        conn.execute(
            role_permissions.delete().where(
                role_permissions.c.permission_code == code
            )
        )
        conn.execute(permissions_table.delete().where(permissions_table.c.code == code))

    with op.batch_alter_table("governance_reports") as batch:
        batch.drop_index("ix_governance_reports_team")
        batch.drop_index("ix_governance_reports_sla_due")
        batch.drop_index("ix_governance_reports_priority")
        batch.drop_column("sla_resolution_due_at")
        batch.drop_column("sla_response_due_at")
        batch.drop_column("first_responded_at")
        batch.drop_column("escalated_by")
        batch.drop_column("escalated_to_team_id")
        batch.drop_column("escalated_at")
        batch.drop_column("team_id")
        batch.drop_column("priority")
    op.drop_table("governance_case_links")
    op.drop_table("governance_team_members")
    op.drop_table("governance_teams")
