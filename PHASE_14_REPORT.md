# PHASE 14 REPORT — ATHENA AI CORE / CONTROLLED INTELLIGENCE PLATFORM

## 1. Objective

Build the foundational, provider-neutral AI/intelligence layer for AskTrabaajo —
an authenticated, authorization-aware, auditable Athena that operates only
through controlled tools and explicit human confirmations, with minimized
context and code-enforced security (never LLM-enforced).

## 2. Starting state

- Phase 13 complete: 164 canonical tests (153 SQLite + 11 PG-only RLS), 192
  `/api/v1` routes, 63 tables through migration 0010, RLS stage-1 enabled on
  six private tables, session-identity mechanism, least-privilege app role,
  legacy backend intact (~107 routes), live Supabase untouched.

## 3. What was built

**Provider abstraction** (`app/services/ai_provider.py`) — `AIProvider` contract
(text generation / structured output / tool calling), OpenAI adapter
(config-driven), provider-neutral error model (`ai.provider_unavailable`,
`ai.rate_limited`, `ai.tool_validation_failed`, `ai.internal`), safe degraded
mode when `AI_PROVIDER=none` (default) — the API returns a clear error and never
fabricates a reply.

**Athena sessions** (`athena_sessions`) — owned, mode-scoped, org-context,
purpose-recorded, lazily expiring (no scheduler), server-derived mode
eligibility.

**Modes** — jobseeker / employer / recruiter operational with tools;
government / platform-operator are architecture-only (zero tools, no
individual-level or auto-enforcement capability).

**Context builder** (`athena_context.py`) — whitelist-only professional digest;
deny-list of sensitive fields enforced by construction + tests.

**Tool registry** (`athena_tools.py`) — 26 declared tools mapping 1:1 to
canonical services, each declaring mode(s), org permission, risk class, data
scope, confirmation requirement, input schema.

**Confirmation framework** (`athena_action_confirmations`) — high-risk writes
(apply, send_message, create_outreach) execute only after an explicit,
single-use, 15-minute-TTL confirmation bound to the exact canonical scope
(scope-hash); stored scope re-validates and re-authorizes at execution.

**Orchestration** (`athena.py`) — bounded chat loop (max 3 turns), persisted
sanitized messages, per-tool authz, audit + usage logging, per-user daily
budgets, rate-limit integration (`athena.chat` / `athena.tool` /
`athena.high_risk`).

**API** — 8 routes under `/api/v1/athena`: `GET /modes`, `GET /tools`,
`POST /session`, `POST /message`, `POST /confirm`, `GET /confirmations`,
`POST /session/{id}/close`, `GET /usage` (own rows only). All authenticated;
no anonymous endpoint.

**Migration 0011** — additive, 63 → 66 tables; validated on scratch SQLite and
scratch PostgreSQL 16 (upgrade clean; full flow exercised on PG). Applied
nowhere real.

**PostgreSQL hardening (finding fixed in-phase)** — scratch PG exposed a
timezone round-trip bug: servers whose session `TimeZone` is not UTC silently
shift stored naive-UTC datetimes, making fresh Athena sessions appear expired.
Every PG connection is now pinned to `SET TIME ZONE 'UTC'`
(`app/db/session.py`), making naive-write → aware-read exact on all dialects.
This also removes the same latent skew from all other canonical timestamp
comparisons. The app-role grant script was updated to cover all 66 tables
(264 DML grants verified).

## 4. Files created (13 + 6 docs)

- `backend/app/models/athena.py` — AthenaSession, AthenaMessage,
  AthenaActionConfirmation, AiUsageLog
- `backend/alembic/versions/0011_athena_ai_core.py` — migration
- `backend/app/services/ai_provider.py` — provider abstraction + OpenAI adapter
- `backend/app/services/athena_tools.py` — 26-tool registry
- `backend/app/services/athena_context.py` — minimized context builder
- `backend/app/services/athena.py` — orchestration/confirmation/usage service
- `backend/app/schemas/athena.py` — API schemas
- `backend/app/api/v1/athena.py` — API routes
- `backend/tests_phase3/test_athena_phase14.py` — 24 adversarial tests
- `PHASE_14_ATHENA_ARCHITECTURE.md`, `PHASE_14_ATHENA_SECURITY.md`,
  `PHASE_14_ATHENA_TOOLS.md`, `PHASE_14_ATHENA_DATA_POLICY.md`,
  `PHASE_14_ATHENA_EVALUATION.md`, `PHASE_14_REPORT.md`

## 5. Files modified (7)

- `backend/app/models/enums.py` — Athena/AI enum constants (modes, message
  roles, session/confirmation statuses, risk classes, AI error codes, audit
  action codes)
- `backend/app/models/__init__.py` — model exports
- `backend/app/core/config.py` — AI provider + limits settings
- `backend/app/core/ratelimit.py` — athena rate-limit policies
- `backend/app/api/v1/router.py` — router registration (192 → 200 routes)
- `backend/app/db/session.py` — PG UTC session pinning
- `scripts/db/app_role.sql` — grants for the 4 new athena tables

## 6. Security results

Proven by the adversarial suite (deterministic fake-provider evaluation, not
LLM-dependent): unknown tools (`run_sql`/`fetch_url`/`read_file`/
`execute_shell`) refused; candidate↔employer tool boundaries; cross-org
application isolation; permission-less role denied (nothing created); prompt
injection cannot expose secrets or trigger applications; malformed args
rejected before authorization; high-risk actions gated by exact-scope,
single-use, expiring confirmations; provider-unavailable degradation; rate
limits + daily budgets; concurrent sessions never cross identities; audit and
usage rows contain no bodies/secrets. RLS suite still green on PG.

## 7. Validation

- Canonical backend suite (SQLite): **177 passed, 11 skipped, 0 failed** —
  no regression from Phase 13's 164.
- RLS suite on scratch PostgreSQL 16: **11 passed** (188 total passing on PG).
- Migration 0011 roundtrip on scratch SQLite + PG; clean DB creation to head
  0011 (66 tables).
- Legacy backend import: PASS, unchanged. Careers/frontend untouched (Phase 14
  is backend infrastructure only; the existing UI was not consumed).

## 8. Production readiness

READY: code-level Athena core (authz, tools, confirmations, minimization,
audit, limits, degradation) with SQLite/PostgreSQL parity. NOT READY /
REQUIRES EXTERNAL INFRASTRUCTURE: a real AI provider credential
(`AI_PROVIDER=openai` + `OPENAI_API_KEY`, or another adapter), production RLS
enablement for the new tables (Phase 13 runbook), retention purge job,
streaming if the future UI needs it. Supabase: NOT TOUCHED (no credentials
available; nothing attempted).

## 9. Known limitations

- No live provider integration (none configured — by design).
- Government / platform-operator modes are shells (architecture only).
- No conversation purge job; retention policy is config-documented.
- No streaming; no embeddings/vector search; no memory — all deliberately
  deferred.

---

PHASE 14 STATUS:
PASS WITH LIMITATIONS

ATHENA CORE:
IMPLEMENTED

AI PROVIDER:
ABSTRACTION ONLY (OpenAI adapter present; no credential configured —
`none` safe default, no fake responses)

ATHENA SESSION:
PASS

TOOL REGISTRY:
PASS

AUTHORIZATION:
PASS

DATA MINIMIZATION:
PASS

PROMPT INJECTION:
PASS

HIGH-RISK ACTIONS:
PASS

AUDIT:
PASS

RATE LIMITING:
PASS

DATABASE:
MIGRATION ADDED (0011, additive 63 → 66; validated on scratch SQLite + PG,
applied nowhere real)

SUPABASE:
NOT TOUCHED

NEW TABLES:
4 — athena_sessions (owned mode-scoped sessions), athena_messages (sanitized
session conversation), athena_action_confirmations (human authorization for
high-risk tool calls), ai_usage_log (provider-neutral usage/cost accounting).
Each justified in PHASE_14_ATHENA_ARCHITECTURE.md §8; none duplicates an
existing domain.

NEW MIGRATIONS:
1 — backend/alembic/versions/0011_athena_ai_core.py

TESTS:
177 PASSED (SQLite canonical suite)
0 FAILED
11 SKIPPED (PG-only RLS suite — 11 PASSED on scratch PostgreSQL 16; 188 total
passing on PG)
0 BLOCKED

SECURITY:
PASS (adversarial + RLS suites green; UTC session-pinning fix verified on PG)

PRODUCTION READINESS:
DEVELOPMENT READY (code-level); STAGING CANDIDATE once a provider credential
and the Phase 13 DB runbook exist

BLOCKERS:
1 — real AI provider credential/selection required for live responses
2 — live Supabase SQL credentials still unavailable (unchanged from Phase 13)
3 — retention purge job + streaming are follow-up work, not blockers

PHASE 15 RECOMMENDATION:
Phase 15 should build the first product surface on this foundation: the
Jobseeker Career Advisor + AI Interview preparation flow using the jobseeker
tool set (get_my_work_id/search_opportunities/compare/get_application_status)
and the confirmation framework for "apply", gated by the same session/mode/
permission architecture. In parallel the provider layer is ready for a real
OpenAI credential in staging once the Phase 13 DB runbook lands. Government and
platform-operator Athena remain architecture-only until their own scoped tool
designs are approved. Phase 15 must NOT weaken any Phase 14 control.
