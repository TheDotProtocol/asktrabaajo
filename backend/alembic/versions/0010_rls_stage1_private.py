"""rls stage 1: owner-scoped policies on strictly private person tables

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-04

STRICTLY ADDITIVE — enables PostgreSQL Row-Level Security on a small,
verified set of tables whose canonical access pattern is owner-read +
owner-write ONLY (no cross-user reads, no cross-user system writes, no
two-party access, no platform-role access). See PHASE_13_RLS_MATRIX.md
for the full design and the staged groups that follow.

Tables (owner column):
  career_goals (person_id), work_dna_profiles (person_id),
  work_dna_answers (person_id), career_milestones (person_id),
  person_visibility_settings (person_id), notification_preferences (user_id)

The policy keys on the canonical session identity
``app.current_user_id`` set per request by the application (Phase 13
session-identity mechanism) — never on ``auth.uid()`` and never on
client-supplied values. RLS is defense in depth; application-level
authorization remains mandatory. Owner/superuser connections bypass RLS,
so production must connect as the least-privilege ``asktrabaajo_app``
role (see scripts/db/app_role.sql).

Policies are created idempotently via DO blocks checking ``pg_policies``
(CREATE POLICY has no IF NOT EXISTS in PostgreSQL <= 16). On SQLite
(dev/test) this migration is a deliberate no-op.

Rollback drops exactly the policies created here and disables RLS on the
same tables; it never touches legacy objects.
"""
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

# (table, owner column) — verified against the canonical models on disk.
PRIVATE_TABLES = [
    ("career_goals", "person_id"),
    ("work_dna_profiles", "person_id"),
    ("work_dna_answers", "person_id"),
    ("career_milestones", "person_id"),
    ("person_visibility_settings", "person_id"),
    ("notification_preferences", "user_id"),
]

_SESSION_USER = "current_setting('app.current_user_id', true)"


def _is_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _policy_sql(table: str, column: str) -> str:
    return (
        f"CREATE POLICY {table}_owner ON {table} "
        f"USING ({column}::text = {_SESSION_USER}) "
        f"WITH CHECK ({column}::text = {_SESSION_USER})"
    )


def upgrade() -> None:
    if not _is_postgres():
        return
    for table, column in PRIVATE_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            "DO $$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' "
            f"AND tablename='{table}' AND policyname='{table}_owner') THEN "
            f"EXECUTE $policy${_policy_sql(table, column)}$policy$; "
            "END IF; END $$;"
        )


def downgrade() -> None:
    if not _is_postgres():
        return
    for table, _column in PRIVATE_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table}_owner ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")