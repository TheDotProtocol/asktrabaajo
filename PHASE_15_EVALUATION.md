# Phase 15 — Evaluation

Phase 15 correctness is proven by **deterministic tests** — the structured
facts are validated independently of any LLM. All fixtures are canonical
platform objects created through the normal registration/setup helpers.

## Test inventory (18 new tests)

`backend/tests_phase3/test_career_interview_phase15.py`

### Career Advisor

| Test | What it proves |
|---|---|
| `test_digest_accuracy_and_minimization` | digest reflects seeded profile/skills/credentials/goals; sensitive tokens absent |
| `test_digest_cross_user_isolation` | digest is always the caller's own — no cross-user leakage |
| `test_career_endpoints_require_auth` | every career route 401s unauthenticated |
| `test_gap_analysis_matched_partial_missing` | matched / partial / missing classification and coverage are exact |
| `test_gap_analysis_unknown_opportunity` | unknown target fails safely, no hallucinated requirements |
| `test_career_paths_direct_and_transition` | classification uses held history vs stated goal (a goal-only target is never `direct`) |
| `test_recommendation_modes` | strong/potential/transition/explore modes return explainable factors |
| `test_application_analysis` | own-history aggregates correct incl. rejected/withdrawn rows |
| `test_action_plan_is_suggestion_only` | action plan mutates nothing |

### Interview Preparation

| Test | What it proves |
|---|---|
| `test_prep_session_lifecycle_and_isolation` | create → questions → answer → complete → delete; **other user gets 404** |
| `test_prep_answers_never_persisted` | after answering, no question/answer content exists in the DB |
| `test_prep_session_lazy_expiry` | expired sessions are treated as expired without any scheduler |
| `test_athena_interview_prep_flow` | full mock flow through Athena tool surface in jobseeker mode |
| `test_prep_audit_contains_no_answer_content` | audit rows carry no answer/narrative content |

### Athena security surface

| Test | What it proves |
|---|---|
| `test_athena_career_tools_run_in_jobseeker_mode` | career tools execute in jobseeker mode |
| `test_employer_cannot_reach_career_or_prep_tools` | employer session → career/prep tool → denied (mode gate) |
| `test_fabrication_attempts_have_no_tool` | "add fake certification / pretend degree" prompts resolve to no tool call |
| `test_athena_apply_to_opportunities_exact_scope_confirmation` | bulk apply requires confirmation; wrong-object / changed-set confirmations never match; execution creates applications via canonical service |

## Confirmations tested

- Single-use: a consumed confirmation cannot be reused.
- Expiry: an expired confirmation is rejected.
- Exact scope: the confirmation payload is a SHA-256 digest of the canonical
  scope (sorted opportunity UUIDs + candidate id); the raw list is not stored.
- Change detection: re-approval re-computes the digest against the **current**
  opportunity list, so a modified set never matches the original confirmation.
- Re-authorization: every opportunity is re-checked at approval time.

## PG coverage (11 Phase-13 RLS tests still green with migration 0012)

The RLS suite passes unchanged on PostgreSQL with the new table present; the
`scripts/db/app_role.sql` grant set (67 tables, 268 privileges) was re-verified.

## End-to-end PostgreSQL smoke (scratch PG 16)

`PG_SMOKE_PASS`: register → career digest/gaps/paths → prep session create →
5 questions → answer evaluation (structured dims) → complete → second user 404
→ owner delete. Proves model↔schema fidelity on `timestamptz` columns (UTC
round-trip) and the owner-isolation path on a real database.

## Latency observation

Test-suite wall time on SQLite is dominated by registration/auth fixtures
(155 s for 206 executions). Individual Phase-15 service calls observed in the
PG smoke are single-digit ms after auth; no AI provider call exists in the
deterministic path, so Phase-15 services cannot block on provider latency by
construction.

## Hallucination posture

- If the platform does not hold a fact (salary, company interview process,
  internal notes), the services say "not available" — they never fabricate.
- Question sets and evaluations are generated deterministically from canonical
  data; model output, when Athena is used, is validated before any action.

## Regression

Full suite: **195 passed / 11 skipped / 0 failed** (SQLite) — no regressions
from Phase 14's 177-passed baseline. The only edited Phase-14 test is the
registry-count assertion (26 → 39 tools), which documents the deliberate Phase
15 extension and re-checks every tool's metadata consistency.
