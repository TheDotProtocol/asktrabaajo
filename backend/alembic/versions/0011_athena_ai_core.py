"""athena ai core: sessions, messages, confirmations, usage log

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-04

STRICTLY ADDITIVE — creates four NEW tables only; no existing table,
column, index, constraint, or policy is touched. No new roles or
permissions (Athena tools reuse the existing permission catalog).
Rollback drops exactly these four tables.

Justification (per Phase 14 §36 — existing tables are insufficient):

- ``athena_sessions``: no existing table represents a per-user, per-mode,
  org-scoped AI conversation context with expiry/audit correlation.
  ``conversations`` is the HUMAN outreach channel (org+person two-party),
  a different domain; reusing it would corrupt outreach semantics.
- ``athena_messages``: ``conversation_messages`` stores human
  recruiter/candidate text with side ownership; Athena messages are
  model-orchestration turns (role user/assistant/tool, validated tool
  call envelopes) with different retention/privacy rules. Separate table
  keeps the two surfaces auditable independently.
- ``athena_action_confirmations``: no existing table stores an explicit
  high-risk action authorization record (requested action + canonical
  scope hash + expiry + actor + decision). ``audit_log`` records what
  happened; this table records what was AUTHORIZED to happen, with a
  pending/approved lifecycle the audit log cannot express.
- ``ai_usage_log``: ``rate_limit_hits`` is an operational counter, not a
  provider usage metric; usage carries model/token/cost/latency and is a
  distinct observability domain.

All four are person/org-scoped, UUID-keyed, indexed, and documented for
the RLS matrix (stage-B person-scoped group; owner/session policies
designed, not enabled — see PHASE_13_RLS_MATRIX.md). Retention: messages
are governed by ``AI_MESSAGE_RETENTION_DAYS``; confirmations expire via
``ATHENA_CONFIRMATION_TTL_MINUTES`` (both lazy, no scheduler dependency).
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
now = sa.text("CURRENT_TIMESTAMP")
tz = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "athena_sessions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="SET NULL")),
        sa.Column("mode", sa.String(24), nullable=False),
        sa.Column("purpose", sa.String(240)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("correlation_id", sa.String(40)),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("last_active_at", tz, server_default=now, nullable=False),
        sa.Column("expires_at", tz),
        sa.Column("closed_at", tz),
    )
    op.create_index("ix_athena_sessions_user_created", "athena_sessions", ["user_id", "created_at"])
    op.create_index("ix_athena_sessions_org_created", "athena_sessions", ["organization_id", "created_at"])

    op.create_table(
        "athena_messages",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("session_id", uuid_type, sa.ForeignKey("athena_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("tool_calls", sa.JSON()),
        sa.Column("provider_model", sa.String(80)),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_athena_messages_session_created", "athena_messages", ["session_id", "created_at"])

    op.create_table(
        "athena_action_confirmations",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("session_id", uuid_type, sa.ForeignKey("athena_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="SET NULL")),
        sa.Column("tool_name", sa.String(80), nullable=False),
        sa.Column("action_summary", sa.String(300)),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("scope_hash", sa.String(64), nullable=False),
        sa.Column("risk_level", sa.String(24), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("authorization_source", sa.String(40), nullable=False),
        sa.Column("created_at", tz, server_default=now, nullable=False),
        sa.Column("expires_at", tz),
        sa.Column("decided_at", tz),
        sa.Column("decided_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("result", sa.JSON()),
        sa.UniqueConstraint(
            "session_id", "tool_name", "scope_hash", "status",
            name="uq_athena_confirmation_scope",
        ),
    )
    op.create_index("ix_athena_confirmations_user_status", "athena_action_confirmations", ["user_id", "status"])
    op.create_index("ix_athena_confirmations_session", "athena_action_confirmations", ["session_id"])

    op.create_table(
        "ai_usage_log",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id", ondelete="SET NULL")),
        sa.Column("session_id", uuid_type, sa.ForeignKey("athena_sessions.id", ondelete="SET NULL")),
        sa.Column("mode", sa.String(24)),
        sa.Column("feature", sa.String(80), nullable=False),
        sa.Column("provider", sa.String(40)),
        sa.Column("model", sa.String(80)),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(60)),
        sa.Column("created_at", tz, server_default=now, nullable=False),
    )
    op.create_index("ix_ai_usage_user_created", "ai_usage_log", ["user_id", "created_at"])
    op.create_index("ix_ai_usage_org_created", "ai_usage_log", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_table("ai_usage_log")
    op.drop_table("athena_action_confirmations")
    op.drop_table("athena_messages")
    op.drop_table("athena_sessions")