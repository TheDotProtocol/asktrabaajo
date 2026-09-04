"""interview prep: candidate-owned preparation session container

Revision ID: 0012
Revises: 0011
Create Date: 2026-09-04

STRICTLY ADDITIVE — creates ONE new table only; no existing table,
column, index, constraint, or policy is touched. No new roles or
permissions (interview prep runs inside the candidate's own jobseeker
scope; REST + Athena tools enforce person ownership). Rollback drops
exactly this table.

Justification (per Phase 15 §38 — existing tables were inspected first):

- ``athena_sessions`` is the generic AI chat context; it carries no
  anchor to an opportunity/application/interview and its lifetime is a
  short chat TTL. A preparation flow must survive across chat sessions
  long enough for the candidate to practice and return.
- ``interviews`` are REAL scheduled interview records from the employer
  pipeline (two-party, status-machine-driven). Mock preparation is a
  candidate-owned practice artifact; storing prep state there would
  corrupt real interview semantics.
- No other existing table can represent a candidate-owned prep artifact
  with an optional job/interview anchor, lazy expiry, and explicit
  owner deletion.

This table stores METADATA ONLY (status, counters, expiry, anchors,
sanitized focus areas). Individual mock answers are NEVER persisted
here: the deterministic prep endpoints return feedback at request time,
and mock runs inside an Athena session keep their turns in
``athena_messages`` under the existing sanitized-message retention
policy (AI_MESSAGE_RETENTION_DAYS). Candidate narratives therefore are
not retained by default, and owners can delete a session at any time.

Person-scoped owner row; RLS stage-B group (owner-read + system-writer
design, matching athena tables; not enabled — see PHASE_13_RLS_MATRIX).
Indexes cover owner lookup and the optional anchors.
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
tz = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "interview_prep_sessions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "person_id",
            uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "application_id",
            uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "interview_id",
            uuid_type,
            sa.ForeignKey("interviews.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "athena_session_id",
            uuid_type,
            sa.ForeignKey("athena_sessions.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("focus_areas", sa.JSON()),
        sa.Column("questions_generated", sa.Integer(), nullable=False),
        sa.Column("answers_evaluated", sa.Integer(), nullable=False),
        sa.Column("last_activity_at", tz, nullable=False),
        sa.Column("expires_at", tz, nullable=False),
        sa.Column("completed_at", tz),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index(
        "ix_interview_prep_sessions_person_id",
        "interview_prep_sessions",
        ["person_id"],
    )
    op.create_index(
        "ix_interview_prep_sessions_opportunity_id",
        "interview_prep_sessions",
        ["opportunity_id"],
    )
    op.create_index(
        "ix_interview_prep_sessions_athena_session_id",
        "interview_prep_sessions",
        ["athena_session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_interview_prep_sessions_athena_session_id",
        table_name="interview_prep_sessions",
    )
    op.drop_index(
        "ix_interview_prep_sessions_opportunity_id",
        table_name="interview_prep_sessions",
    )
    op.drop_index(
        "ix_interview_prep_sessions_person_id",
        table_name="interview_prep_sessions",
    )
    op.drop_table("interview_prep_sessions")
