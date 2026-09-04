"""ai interview engine: orchestration envelope tables (Phase 16)

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-04

STRICTLY ADDITIVE — creates FOUR tables only; no existing table, column,
index, constraint, or policy is touched. Rollback drops exactly these
tables.

Justification (per Phase 16 §43/§63 — existing tables were inspected):

- ``interviews`` are REAL scheduled interview records in the employer
  pipeline (two-party, status-machine-driven). The AI interview is a
  distinct orchestration domain with its own consent, entry-token,
  media, integrity-signal and human-decision lifecycle; storing it in
  ``interviews`` would corrupt real interview semantics and leak a
  candidate-entry mechanism into employer scheduling data.
- ``athena_sessions`` / ``athena_messages`` are chat envelopes with a
  short TTL; an interview plan must persist for the whole flow, be
  re-entrant across pauses, and carry employer configuration.
- ``interview_prep_sessions`` is candidate-owned PRACTICE metadata
  (mock interviews); the AI interview is an EMPLOYER-invited,
  consent-governed assessment flow with a different tenant model
  (organization + candidate) and different lifecycle.
- No existing table can represent the validated question plan, the
  structured per-question evaluation, or the completion report.

FOUR new tables:

1. ``ai_interview_sessions`` — employer-configured, candidate-owned
   flow: state machine, consent snapshot, entry-token hash, media
   profile, bounded integrity signals, human decision. Raw answers,
   transcripts and media are never stored.
2. ``ai_interview_questions`` — the validated, sequenced question plan
   (grounded in job requirements + candidate Work ID; prohibited-topic
   gate enforced at generation time).
3. ``ai_interview_evaluations`` — structured per-question evaluation on
   explainable dimensions. NO raw answer text.
4. ``ai_interview_reports`` — completion report marked AI-assisted /
   human-review-required.

Tenancy: organization + candidate person. Service/API layer enforces
tenant and person ownership; the candidate entry path additionally
requires the SHA-256 entry-token match (token itself is returned once at
creation and never stored). RLS: designed for the future stage-B/C
groups; not enabled in this phase (see PHASE_13_RLS_MATRIX).
"""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

uuid_type = sa.Uuid()
tz = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "ai_interview_sessions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "organization_id",
            uuid_type,
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_id",
            uuid_type,
            sa.ForeignKey("job_applications.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "opportunity_id",
            uuid_type,
            sa.ForeignKey("opportunities.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "interview_id",
            uuid_type,
            sa.ForeignKey("interviews.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "candidate_person_id",
            uuid_type,
            sa.ForeignKey("person_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("interview_type", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("question_count", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(16), nullable=False),
        sa.Column("competencies", sa.JSON()),
        sa.Column("evaluation_dimensions", sa.JSON()),
        sa.Column("introduction", sa.Text()),
        sa.Column("closing", sa.Text()),
        sa.Column("media_profile", sa.JSON()),
        sa.Column("consent_required", sa.Boolean(), nullable=False),
        sa.Column("consent_granted_at", tz),
        sa.Column("consent_version", sa.String(20)),
        sa.Column("consent_mic", sa.Boolean(), nullable=False),
        sa.Column("consent_camera", sa.Boolean(), nullable=False),
        sa.Column("consent_recording", sa.Boolean(), nullable=False),
        sa.Column("consent_withdrawn_at", tz),
        sa.Column("entry_token_hash", sa.String(64), nullable=False),
        sa.Column("started_at", tz),
        sa.Column("completed_at", tz),
        sa.Column("cancelled_at", tz),
        sa.Column("cancel_reason", sa.String(40)),
        sa.Column("expires_at", tz),
        sa.Column("failed_reason", sa.String(60)),
        sa.Column("integrity_signals", sa.JSON()),
        sa.Column("decision", sa.String(32)),
        sa.Column("decision_note", sa.String(500)),
        sa.Column("decided_by", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("decided_at", tz),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index(
        "ix_ai_interviews_org_created", "ai_interview_sessions", ["organization_id", "created_at"]
    )
    op.create_index(
        "ix_ai_interviews_person_created",
        "ai_interview_sessions",
        ["candidate_person_id", "created_at"],
    )
    op.create_index(
        "ix_ai_interviews_application_id", "ai_interview_sessions", ["application_id"]
    )
    op.create_index("ix_ai_interviews_opportunity_id", "ai_interview_sessions", ["opportunity_id"])
    op.create_index("ix_ai_interviews_interview_id", "ai_interview_sessions", ["interview_id"])
    op.create_index("ix_ai_interviews_person_id", "ai_interview_sessions", ["candidate_person_id"])

    op.create_table(
        "ai_interview_questions",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "session_id",
            uuid_type,
            sa.ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(24), nullable=False),
        sa.Column("competency", sa.String(80), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("difficulty", sa.String(16), nullable=False),
        sa.Column("target_skill", sa.String(120)),
        sa.Column("reason", sa.Text()),
        sa.Column("suggested_dimensions", sa.JSON()),
        sa.Column("follow_ups", sa.JSON()),
        sa.Column(
            "follow_up_of",
            uuid_type,
            sa.ForeignKey("ai_interview_questions.id", ondelete="CASCADE"),
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("asked_at", tz),
        sa.Column("answered_at", tz),
        sa.UniqueConstraint("session_id", "sequence", name="uq_ai_interview_question_sequence"),
    )
    op.create_index(
        "ix_ai_interview_questions_session", "ai_interview_questions", ["session_id", "sequence"]
    )
    op.create_index(
        "ix_ai_interview_questions_follow_up_of", "ai_interview_questions", ["follow_up_of"]
    )

    op.create_table(
        "ai_interview_evaluations",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "session_id",
            uuid_type,
            sa.ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            uuid_type,
            sa.ForeignKey("ai_interview_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dimensions", sa.JSON(), nullable=False),
        sa.Column("strengths", sa.JSON()),
        sa.Column("improvements", sa.JSON()),
        sa.Column("evidence_markers", sa.JSON()),
        sa.Column("follow_up_used", sa.String(24)),
        sa.Column("answer_length", sa.Integer(), nullable=False),
        sa.Column("created_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("session_id", "question_id", name="uq_ai_interview_eval_question"),
    )
    op.create_index("ix_ai_interview_evaluations_session", "ai_interview_evaluations", ["session_id"])

    op.create_table(
        "ai_interview_reports",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "session_id",
            uuid_type,
            sa.ForeignKey("ai_interview_sessions.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("competency_evidence", sa.JSON()),
        sa.Column("strengths", sa.JSON()),
        sa.Column("improvement_areas", sa.JSON()),
        sa.Column("unanswered_areas", sa.JSON()),
        sa.Column("integrity_signals", sa.JSON()),
        sa.Column("interview_quality", sa.JSON()),
        sa.Column("generated_by_user_id", uuid_type, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("generated_at", tz, server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("ai_interview_reports")
    op.drop_index("ix_ai_interview_evaluations_session", table_name="ai_interview_evaluations")
    op.drop_table("ai_interview_evaluations")
    op.drop_index("ix_ai_interview_questions_session", table_name="ai_interview_questions")
    op.drop_index("ix_ai_interview_questions_follow_up_of", table_name="ai_interview_questions")
    op.drop_table("ai_interview_questions")
    op.drop_index("ix_ai_interviews_person_id", table_name="ai_interview_sessions")
    op.drop_index("ix_ai_interviews_interview_id", table_name="ai_interview_sessions")
    op.drop_index("ix_ai_interviews_opportunity_id", table_name="ai_interview_sessions")
    op.drop_index("ix_ai_interviews_application_id", table_name="ai_interview_sessions")
    op.drop_index("ix_ai_interviews_person_created", table_name="ai_interview_sessions")
    op.drop_index("ix_ai_interviews_org_created", table_name="ai_interview_sessions")
    op.drop_table("ai_interview_sessions")