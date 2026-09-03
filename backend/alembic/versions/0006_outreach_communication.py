"""controlled talent outreach & communication: outreach_requests, blocks,
conversations, messages, read states

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-03

STRICTLY ADDITIVE and safe:
- Creates five brand-new canonical tables for the Phase 8 controlled
  outreach / communication layer (none of these names exist in the live
  Supabase careers schema — nothing legacy is touched).
- Seeds Phase 8 permissions (talent.outreach.*, communications.*) and
  role mappings into the canonical RBAC catalog (idempotent by PK).
Rollback drops exactly what this revision created.

New tables: outreach_requests, outreach_blocks, conversations,
            conversation_messages, conversation_read_states
"""
import uuid

from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
now = sa.text("CURRENT_TIMESTAMP")
tz = sa.DateTime(timezone=True)

NEW_PERMISSIONS = [
    ("talent.outreach.create", "Send outreach requests to candidates"),
    ("talent.outreach.read", "Read the organization's outreach requests"),
    ("talent.outreach.manage", "Manage/cancel the organization's outreach requests"),
    ("communications.read", "Read the organization's candidate conversations"),
    ("communications.send", "Send messages in the organization's conversations"),
    ("communications.manage", "Manage/close the organization's conversations"),
]
ROLE_ADDITIONS = {
    "org_admin": [
        "talent.outreach.create", "talent.outreach.read", "talent.outreach.manage",
        "communications.read", "communications.send", "communications.manage",
    ],
    "hr": [
        "talent.outreach.create", "talent.outreach.read", "talent.outreach.manage",
        "communications.read", "communications.send", "communications.manage",
    ],
    "recruiter": [
        "talent.outreach.create", "talent.outreach.read",
        "communications.read", "communications.send",
    ],
    "hiring_manager": ["communications.read"],
}


def upgrade() -> None:
    # ---- outreach_requests ----------------------------------------------------
    op.create_table(
        "outreach_requests",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "requester_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "opportunity_id", uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "application_id", uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="SET NULL"),
        ),
        sa.Column("conversation_id", uuid_type),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("context", sa.String(300)),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("expires_at", tz),
        sa.Column("viewed_at", tz),
        sa.Column("responded_at", tz),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint(
            "organization_id", "person_id", "opportunity_id", "status",
            name="uq_outreach_org_person_opp_status",
        ),
        sa.UniqueConstraint("conversation_id", name="uq_outreach_conversation"),
    )
    op.create_index(
        "ix_outreach_requests_organization_id", "outreach_requests", ["organization_id"]
    )
    op.create_index(
        "ix_outreach_requests_person_id", "outreach_requests", ["person_id"]
    )
    op.create_index(
        "ix_outreach_requests_opportunity_id", "outreach_requests", ["opportunity_id"]
    )

    # ---- outreach_blocks ------------------------------------------------------
    op.create_table(
        "outreach_blocks",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "created_by", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.String(300)),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint(
            "person_id", "organization_id", name="uq_outreach_blocks_person_org"
        ),
    )
    op.create_index("ix_outreach_blocks_person_id", "outreach_blocks", ["person_id"])
    op.create_index(
        "ix_outreach_blocks_organization_id", "outreach_blocks", ["organization_id"]
    )

    # ---- conversations --------------------------------------------------------
    op.create_table(
        "conversations",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id", uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "person_id", uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "opportunity_id", uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "application_id", uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "outreach_id", uuid_type,
            sa.ForeignKey("outreach_requests.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "opened_by", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("last_message_at", tz),
        sa.Column(
            "closed_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column("closed_at", tz),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])
    op.create_index("ix_conversations_person_id", "conversations", ["person_id"])
    op.create_index("ix_conversations_last_message_at", "conversations", ["last_message_at"])

    # ---- conversation_messages -------------------------------------------------
    op.create_table(
        "conversation_messages",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "conversation_id", uuid_type,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "sender_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sender_side", sa.String(16), nullable=False,
                  server_default="recruiter"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index(
        "ix_conversation_messages_conversation_id", "conversation_messages",
        ["conversation_id"],
    )

    # ---- conversation_read_states ---------------------------------------------
    op.create_table(
        "conversation_read_states",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "conversation_id", uuid_type,
            sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("last_read_at", tz, server_default=now, nullable=False),
        sa.Column("updated_at", tz, server_default=now, nullable=False),
        sa.UniqueConstraint(
            "conversation_id", "user_id", name="uq_conversation_read_state"
        ),
    )
    op.create_index(
        "ix_conversation_read_states_conversation_id", "conversation_read_states",
        ["conversation_id"],
    )

    # ---- RBAC: Phase 8 permissions + role mappings -----------------------------
    permissions_table = sa.table(
        "permissions",
        sa.column("code", sa.String),
        sa.column("name", sa.String),
    )
    for code, name in NEW_PERMISSIONS:
        exists = op.get_bind().execute(
            sa.select(sa.literal(1)).select_from(permissions_table).where(
                permissions_table.c.code == code
            )
        ).first()
        if exists is None:
            op.get_bind().execute(
                permissions_table.insert().values(code=code, name=name)
            )

    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_code", sa.String),
        sa.column("permission_code", sa.String),
    )
    for role_code, codes in ROLE_ADDITIONS.items():
        for permission_code in codes:
            exists = op.get_bind().execute(
                sa.select(sa.literal(1)).select_from(role_permissions).where(
                    role_permissions.c.role_code == role_code,
                    role_permissions.c.permission_code == permission_code,
                )
            ).first()
            if exists is None:
                op.get_bind().execute(
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

    op.drop_index(
        "ix_conversation_read_states_conversation_id", table_name="conversation_read_states"
    )
    op.drop_table("conversation_read_states")
    op.drop_index(
        "ix_conversation_messages_conversation_id", table_name="conversation_messages"
    )
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversations_last_message_at", table_name="conversations")
    op.drop_index("ix_conversations_person_id", table_name="conversations")
    op.drop_index("ix_conversations_organization_id", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_outreach_blocks_organization_id", table_name="outreach_blocks")
    op.drop_index("ix_outreach_blocks_person_id", table_name="outreach_blocks")
    op.drop_table("outreach_blocks")
    op.drop_index(
        "ix_outreach_requests_opportunity_id", table_name="outreach_requests"
    )
    op.drop_index("ix_outreach_requests_person_id", table_name="outreach_requests")
    op.drop_index(
        "ix_outreach_requests_organization_id", table_name="outreach_requests"
    )
    op.drop_table("outreach_requests")
