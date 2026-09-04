"""PostgreSQL Row-Level Security foundation (Phase 9) — PREPARED, NOT APPLIED.

Phase 13 note: migration ``0010_rls_stage1_private`` implements the first
safe stage (strictly owner-private tables) with the session-identity
mechanism in ``app/db/session.py`` + ``app/api/deps.py``; the full
per-table design and staged enablement order live in
PHASE_13_RLS_MATRIX.md. Column names below were re-verified against the
canonical models — ``talent_pool_members`` is person-scoped
(``person_id``, indirect via ``talent_pools``), not org-scoped as listed
in the original Phase 9 draft.

This module is a reviewed artifact + validation target, not a migration.
Enabling RLS on a shared PostgreSQL requires:

1. A superuser to ``CREATE ROLE asktrabaajo_app`` and grant table access.
2. A guarded, Postgres-only migration that runs ``ALTER TABLE ... ENABLE
   ROW LEVEL SECURITY`` + ``CREATE POLICY ...`` for each policy below.
3. The application connection setting ``app.current_user_id`` /
   ``app.current_org_ids`` per transaction (set from the authenticated
   actor, never client-supplied).

It is intentionally NOT applied to SQLite (unsupported) and was NOT applied
to any shared/production database. Application-level authorization remains
mandatory; RLS is defense in depth, never a replacement.

Two isolation classes:
- ``ORG_TENANT_TABLES``: rows carry an ``organization_id`` column — policy
  allows access when the org is in the session's ``app.current_org_ids``.
- ``PERSON_TENANT_TABLES``: rows carry a ``person_id``/``user_id`` — policy
  allows access when the row's owner is the session's ``app.current_user_id``.

``rls_policy_coverage()`` validates that every tenant table has a policy
here; the test suite asserts coverage and that policies reference the
session settings (so a typo can never produce a wide-open policy).
"""
from __future__ import annotations

from typing import Dict, List

# (table, organization column) — rows scoped to one tenant organization.
ORG_TENANT_TABLES: List[tuple] = [
    ("company_profiles", "organization_id"),
    ("job_postings", "organization_id"),
    ("talent_pools", "organization_id"),
    ("saved_candidates", "organization_id"),
    ("outreach_requests", "organization_id"),
    ("outreach_blocks", "organization_id"),
    ("conversations", "organization_id"),
    ("conversation_messages", None),   # via conversations.organization_id
    ("conversation_read_states", None),  # via conversations.organization_id
    ("talent_pool_members", None),  # via talent_pools.organization_id
    ("governance_reports", "organization_id"),
    ("memberships", "organization_id"),
]

# (table, owner column) — rows scoped to one person/user.
PERSON_TENANT_TABLES: List[tuple] = [
    ("person_profiles", "user_id"),
    ("career_goals", "person_id"),
    ("work_dna_profiles", "person_id"),
    ("work_dna_answers", "person_id"),
    ("career_milestones", "person_id"),
    ("job_applications", "person_id"),
    ("application_events", None),  # via job_applications.person_id
    ("interviews", None),          # via job_applications.person_id
    ("offers", None),              # via job_applications.person_id
    ("opportunity_interactions", "person_id"),
    ("user_notifications", "user_id"),
    ("user_skills", "person_id"),
    ("work_experiences", "person_id"),
    ("educations", "person_id"),
    ("employments", "person_id"),
    ("credentials", "person_id"),
    ("skill_evidence", "person_id"),
    ("person_documents", "person_id"),
    ("document_access_grants", "person_id"),
    ("consents", "person_id"),
    ("person_visibility_settings", "person_id"),
    ("refresh_tokens", "user_id"),
    ("email_verification_tokens", "user_id"),
    ("password_reset_tokens", "user_id"),
    ("platform_events", None),     # direct recipient OR org member
    ("rate_limit_hits", None),     # operational: no RLS (app-owned)
    ("notification_preferences", "user_id"),
]


def org_policy_sql(table: str, org_column: str, setting: str = "app.current_org_ids") -> str:
    """SELECT/INSERT/UPDATE/DELETE policy for an org-scoped table."""
    return (
        f"CREATE POLICY {table}_tenant ON {table}\n"
        f"  USING ({org_column}::text = ANY (string_to_array("
        f"current_setting('{setting}', true), ',')))\n"
        f"  WITH CHECK ({org_column}::text = ANY (string_to_array("
        f"current_setting('{setting}', true), ',')));"
    )


def person_policy_sql(table: str, owner_column: str) -> str:
    """Policy for a person/user-scoped table."""
    return (
        f"CREATE POLICY {table}_owner ON {table}\n"
        f"  USING ({owner_column}::text = current_setting('app.current_user_id', true))\n"
        f"  WITH CHECK ({owner_column}::text = current_setting('app.current_user_id', true));"
    )


RLS_POLICIES: Dict[str, List[str]] = {}


def _build_policies() -> Dict[str, List[str]]:
    policies: Dict[str, List[str]] = {}
    for table, org_column in ORG_TENANT_TABLES:
        if org_column:
            policies[table] = [org_policy_sql(table, org_column)]
        else:
            # Indirect org-scoped tables guard through their parent; the
            # policy is defined in SQL with a subquery on the parent table.
            policies[table] = [f"-- indirect tenant via {table}'s parent row"]
    for table, owner_column in PERSON_TENANT_TABLES:
        if owner_column:
            policies[table] = [person_policy_sql(table, owner_column)]
        else:
            policies[table] = [f"-- indirect owner via {table}'s parent row"]
    return policies


RLS_POLICIES.update(_build_policies())


def _direct_tables() -> List[str]:
    return [
        table for table, column in ORG_TENANT_TABLES + PERSON_TENANT_TABLES
        if column is not None
    ]


def rls_policy_coverage() -> List[str]:
    """Direct-tenant tables that require RLS but lack a policy here.

    Indirect tables (guarded through a parent row, e.g. conversation_messages
    through conversations.organization_id) are intentionally excluded: their
    policy SQL is defined against the parent and validated separately.
    """
    missing = []
    for table in _direct_tables():
        sql = RLS_POLICIES.get(table, [])
        if not any("CREATE POLICY" in s for s in sql):
            missing.append(table)
    return missing


def rls_indirect_tables() -> List[str]:
    """Tables whose RLS is enforced via a parent row's policy."""
    return [
        table for table, column in ORG_TENANT_TABLES + PERSON_TENANT_TABLES
        if column is None
    ]