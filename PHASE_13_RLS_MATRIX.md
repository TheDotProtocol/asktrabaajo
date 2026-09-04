# PHASE 13 — RLS MATRIX

The full per-table Row-Level Security design for the canonical schema
(62 tables, migrations 0001–0010). Groups:

- **A — ENABLED (migration 0010, validated on PostgreSQL):** strictly
  owner-read + owner-write private tables. No cross-user reads, no
  cross-user system writes, no two-party access — so a plain owner
  policy is provably correct today.
- **B — DESIGNED, STAGED NEXT:** tables with legitimate two-party access
  or system-writer paths. Enabling naive owner policies would break
  authorized application flows; each needs its designed policy plus the
  deployment mechanism (non-owner app role live + app switching to it).
- **C — DESIGNED, NEEDS PLATFORM-ROLE SESSION:** tables whose access is
  role-based (governance/enforcement/appeals/membership management).
  Needs an `app.current_roles` session GUC and role-membership policies.
- **D — OPERATIONAL / NO TENANT RLS:** catalog, audit, rate-limit, and
  public discovery tables.

Session identity: `app.current_user_id` (person) and
`app.current_org_ids` (comma-separated org UUIDs) are set per request by
the canonical app from the authenticated actor — never from client input —
and reset on request end (pool-safe). Owner/superuser roles bypass RLS;
production must connect as `asktrabaajo_app` (scripts/db/app_role.sql).

## A — ENABLED in migration 0010 (6 tables)

| Table | OWNER | TENANT | ROLE | ACTION | POLICY |
|---|---|---|---|---|---|
| career_goals | person | person | any authenticated person | ALL | `person_id = current_user_id` |
| work_dna_profiles | person | person | any authenticated person | ALL | `person_id = current_user_id` |
| work_dna_answers | person | person | any authenticated person | ALL | `person_id = current_user_id` |
| career_milestones | person | person | any authenticated person | ALL | `person_id = current_user_id` |
| person_visibility_settings | person | person | any authenticated person | ALL | `person_id = current_user_id` |
| notification_preferences | user | user | any authenticated user | ALL | `user_id = current_user_id` |

Rationale for enabling these first: each row's only reader and writer is
its owner (verified against services); there is no system-write path for
another user and no disclosure path. They are the highest-sensitivity
private data ("private career goals" is explicitly product-private).

## B — DESIGNED, STAGED NEXT (two-party / system-writer)

| Table | OWNER | TENANT | ROLE | POLICY (designed) |
|---|---|---|---|---|
| person_profiles | person | person | person + authorized orgs | `user_id = current_user_id OR visibility-grant exists` (via person_visibility_settings / disclosure) |
| user_skills, work_experiences, educations, employments, credentials, skill_evidence | person | person | person + talent-graph readers | owner OR active disclosure grant (consent-controlled) |
| person_documents | person | person | person + grant holders | owner OR `document_access_grants` active grant |
| document_access_grants | person | person | person + requester | `person_id = current_user_id OR grantee_user_id = current_user_id OR grantee_organization_id ∈ current_org_ids` |
| consents | person | person | person + grantee | same three-way condition as grants |
| job_applications | person | person(org via opportunity) | person + owning org | `person_id = current_user_id OR opportunity → job_posting.organization_id ∈ current_org_ids` |
| application_events, interviews, offers | (via application) | org | both parties | parent-subquery on job_applications (owner OR org) |
| outreach_requests | org + person | org/person | org sender + candidate | `organization_id ∈ current_org_ids OR person_id = current_user_id` |
| outreach_blocks | person/org | org | org | `organization_id ∈ current_org_ids` |
| conversations | org + person | org/person | both parties | `organization_id ∈ current_org_ids OR person_id = current_user_id` |
| conversation_messages, conversation_read_states | (via conversation) | org/person | both parties | parent-subquery on conversations (org OR person) |
| opportunity_interactions | person | person | person + platform | `person_id = current_user_id` (verify platform reads before enabling) |
| talent_pool_members | (via talent_pools) | org | org | parent-subquery on talent_pools.organization_id |
| company_profiles, job_postings, talent_pools, saved_candidates | org | org | org members | `organization_id ∈ current_org_ids` (job_postings public read + org write split into two policies) |
| refresh_tokens, email_verification_tokens, password_reset_tokens | user | user | owner + auth service | owner policy + SECURITY DEFINER/system-writer function for unauthenticated flows (reset/verify) — needs the elevated-writer mechanism first |
| user_notifications | user | user | owner + system writer | owner OR system-writer path (notifications are inserted for other users by services) |

## C — DESIGNED, NEEDS PLATFORM-ROLE SESSION (`app.current_roles`)

| Table | Design |
|---|---|
| governance_reports, governance_report_notes, governance_case_links, governance_teams, governance_team_members | platform-role policy: reporter org OR moderator/auditor role membership via `app.current_roles` |
| enforcement_actions, appeals | platform-role policy: enforcement/appeals permissions via `app.current_roles`; appeals additionally owner-visible to the appellant |
| memberships | bootstrap-safe: `user_id = current_user_id OR organization_id ∈ current_org_ids` (must allow the auth bootstrap query) |
| users | NOT owner-RLS — read during authentication before any session identity exists; needs service-role separation or SECURITY DEFINER access path; app-level authz remains authoritative |
| organizations | platform/admin access pattern; no tenant RLS (top of the tenant tree) |
| audit_log, platform_events | platform read + correlation; audit-reader roles; no tenant RLS (immutable, app-gated) |

## D — OPERATIONAL / NO TENANT RLS

`rate_limit_hits` (operational), `roles`, `permissions`, `role_permissions`
(catalog), `skills`, `skill_aliases`, `skill_relationships`, `career_paths`,
`career_path_steps` (catalog), `opportunities`, `opportunity_requirements`
(public discovery), `candidate_search_events` (operational metrics).

## Coverage accounting

- 62 canonical tables; 6 in A (enabled), 24 in B (designed-staged),
  8 in C (designed-staged, needs roles GUC), 8 in D (no tenant RLS),
  remainder catalog/operational included in D/B as listed.

## Validation performed

- Migration 0010 upgrade → downgrade → re-upgrade on local PostgreSQL 16
  (policies created idempotently, dropped cleanly).
- Hostile matrix (11 tests, `tests_phase3/test_rls_phase13.py`) green
  against a scratch PG with the `asktrabaajo_app` role: cross-user
  read/update/delete denied (0 rows), unauthenticated INSERT blocked by
  WITH CHECK, unauthenticated reads return 0 rows, own-row inserts
  succeed, runtime role cannot DDL, runtime role has no legacy-schema
  privileges, session identity does not leak across concurrent sessions,
  config guard keeps the mechanism inert unless enabled.
- Live project: RLS **not enabled** there (no live changes made; blocked
  on credentials). Groups B/C are the documented next stages — never to
  be enabled blindly.