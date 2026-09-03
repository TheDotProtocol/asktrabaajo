"""0009 — Moderator enforcement + appeals (Phase 11).

Strictly additive:

- ``enforcement_actions`` — one explicit, granular, audited action against a
  target user and/or organization, tied to a governance case. Action type,
  scope, reason code and lifecycle are controlled values. Severe actions
  require an approval separation (creator != approver). ACTIVE/EXPIRED are
  deterministic from ``effective_at``/``expires_at`` — correctness never
  depends on a background scheduler. ``supersedes_id`` supports the appeal
  chain (a reinstatement/reduction replaces the action it supersedes).
- ``appeals`` — an enforcement target's controlled appeal. Decisions never
  silently mutate the original action; an accepted/partial appeal creates a
  new superseding action recorded on ``superseding_action_id``.

RBAC: adds ``enforcement.*`` and ``appeals.*`` permissions plus the platform
``enforcement_manager`` role. Moderators receive read-only visibility for
case context only — never enforcement powers. Nothing is dropped; no data is
rewritten. Validated on scratch/local databases only.
"""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

UUID = sa.Uuid()  # cross-dialect (SQLite + Postgres) like migrations 0005-0008
tz = sa.DateTime(timezone=True)
now = sa.text("CURRENT_TIMESTAMP")

NEW_ROLES = [
    ("enforcement_manager", "Enforcement Manager", "platform",
     "Proposes/approves/revokes controlled enforcement actions and decides "
     "eligible appeals. Severe actions require creator != approver."),
]
NEW_PERMISSIONS = [
    ("enforcement.read", "Read enforcement actions and their lifecycle"),
    ("enforcement.create", "Propose controlled enforcement actions"),
    ("enforcement.approve", "Approve/reject proposed enforcement actions"),
    ("enforcement.revoke", "Revoke or expire active enforcement actions"),
    ("enforcement.reinstate", "Restore access after an enforcement action"),
    ("appeals.read", "Read appeals and their eligibility"),
    ("appeals.manage", "Assign and review appeals"),
    ("appeals.decide", "Decide appeals (uphold/reduce/revoke/reinstate)"),
]
ROLE_ADDITIONS = {
    # Moderators can see enforcement/appeal context on their cases — never
    # create, approve or decide. That power belongs to enforcement managers.
    "moderator": ["enforcement.read", "appeals.read"],
    "enforcement_manager": [
        "users.read", "orgs.read",
        "reports.read", "reports.audit",
        "enforcement.read", "enforcement.create", "enforcement.approve",
        "enforcement.revoke", "enforcement.reinstate",
        "appeals.read", "appeals.manage", "appeals.decide",
    ],
    "super_admin": [c for c, _n in NEW_PERMISSIONS],
}


def upgrade() -> None:
    conn = op.get_bind()

    # ---- enforcement_actions ---------------------------------------------------
    op.create_table(
        "enforcement_actions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "governance_case_id", UUID,
            sa.ForeignKey("governance_reports.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "target_user_id", UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "target_organization_id", UUID,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
        ),
        sa.Column("action_type", sa.String(40), nullable=False),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(40), nullable=False,
                  server_default="other"),
        sa.Column("note", sa.String(500)),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="proposed"),
        sa.Column(
            "created_by", UUID,
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "approved_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("approval_note", sa.String(500)),
        sa.Column(
            "rejected_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("rejection_note", sa.String(500)),
        sa.Column(
            "revoked_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("revoke_note", sa.String(500)),
        sa.Column("effective_at", tz, nullable=False),
        sa.Column("expires_at", tz),
        sa.Column("activated_at", tz),
        sa.Column("revoked_at", tz),
        sa.Column(
            "supersedes_id", UUID,
            sa.ForeignKey("enforcement_actions.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_enforcement_actions_target_user", "enforcement_actions",
        ["target_user_id", "status"],
    )
    op.create_index(
        "ix_enforcement_actions_target_org", "enforcement_actions",
        ["target_organization_id", "status"],
    )
    op.create_index(
        "ix_enforcement_actions_case", "enforcement_actions",
        ["governance_case_id"],
    )
    op.create_index(
        "ix_enforcement_actions_scope_type", "enforcement_actions",
        ["scope", "action_type"],
    )

    # ---- appeals ----------------------------------------------------------------
    op.create_table(
        "appeals",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "enforcement_action_id", UUID,
            sa.ForeignKey("enforcement_actions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "appellant_user_id", UUID,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason_code", sa.String(40), nullable=False,
                  server_default="other"),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False,
                  server_default="submitted"),
        sa.Column(
            "assigned_reviewer_id", UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column("review_note", sa.Text()),
        sa.Column(
            "decided_by", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("decision", sa.String(20)),
        sa.Column("decision_note", sa.String(1000)),
        sa.Column("decided_at", tz),
        sa.Column("withdrawn_at", tz),
        sa.Column(
            "superseding_action_id", UUID,
            sa.ForeignKey("enforcement_actions.id", ondelete="SET NULL"),
        ),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_appeals_appellant", "appeals", ["appellant_user_id", "status"],
    )
    op.create_index(
        "ix_appeals_reviewer", "appeals",
        ["assigned_reviewer_id", "status"],
    )
    op.create_index("ix_appeals_action", "appeals", ["enforcement_action_id"])
    op.create_index(
        "ix_appeals_superseding_action", "appeals", ["superseding_action_id"],
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

    op.drop_table("appeals")
    op.drop_table("enforcement_actions")
