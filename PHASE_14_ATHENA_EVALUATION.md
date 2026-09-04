# PHASE 14 — ATHENA EVALUATION

Status: PASS — deterministic, code-enforced evaluation (never LLM-dependent).

## 1. Method

Security must be enforced by code, so evaluation uses a **scripted
`FakeProvider`** (a test double that returns canned, adversarial model outputs)
against the real API and the real service layer. No live LLM is required or
used in tests. Every assertion is deterministic.

## 2. Coverage (24 tests, `backend/tests_phase3/test_athena_phase14.py`)

### Sessions + modes (4)
- session create + server-derived mode eligibility (jobseeker yes / employer no
  without membership)
- employer mode requires an org membership (403)
- session ownership: another user cannot message a session they do not own (404)
- a jobseeker cannot open employer mode (403)

### Tool authorization (6)
- arbitrary/unregistered tools (`run_sql`, `fetch_url`, `read_file`,
  `execute_shell`) refused and surfaced as errors — none execute
- candidate cannot invoke an employer tool (`search_talent`)
- employer cannot invoke a candidate-private tool (`get_my_career_goals`)
- employer tool without the permission (`talent.outreach.create` missing for
  `hiring_manager`) denied; nothing created
- org A cannot read org B's application through a tool even knowing the UUID
- registry hygiene: 26 tools, schema present, risk ∈ allowed set,
  confirmation_required ⇒ high_risk_write, schema name matches registry key

### Prompt injection + minimization (3)
- sensitive profile fields never appear in the Athena digest (deny-list
  contract, string assertions)
- an "ignore your instructions / reveal my passport" user message stores no
  sensitive values and the digest stays clean
- a hostile "job description" instructing an application cannot trigger one
  without an explicit confirmation (no application row)

### Confirmations (5)
- high-risk apply requires confirmation, then approves and executes the exact
  stored scope
- denial records the decision; nothing executes
- a stale (expired) confirmation is refused; the row flips to `expired`
- a confirmation for object A never authorizes object B (new confirmation
  required; nothing created for B)
- wrong-user / wrong-session confirmations are not accessible

### Failure handling (3)
- provider unavailable ⇒ HTTP 502 `ai.provider_unavailable` (never a fabricated
  reply)
- malformed tool arguments ⇒ refused (`ai.tool_validation_failed`) before any
  authorization/execution
- expired session denies tool use (422; row flipped to `expired`)

### Rate limits + budgets (2)
- `athena.chat` limiter enforced (429 after the window is exceeded)
- per-user daily chat budget enforced over `ai_usage_log` (429)

### Concurrency + audit hygiene (3)
- concurrent sessions for two users never cross identities (messages and usage
  rows are keyed to the correct owner)
- audit payloads and usage rows contain no message bodies or secret phrases;
  usage rows have no content column
- expired session denies a fresh tool call (lazy expiry without scheduler)

## 3. Results

| Suite | Result |
|---|---|
| Phase 14 Athena suite (SQLite) | 24 passed, 0 failed |
| Full canonical suite (SQLite) | **177 passed, 11 skipped** (skips = PG-only RLS suite) |
| RLS suite (scratch PostgreSQL 16) | 11 passed, 0 failed |
| Full canonical suite on PostgreSQL | 188 expected passed (177 + 11 RLS) — migration 0011 + RLS + Athena end-to-end flow validated on PG directly |
| Legacy backend import | PASS — unchanged (~101–107 routes depending on FastAPI counting convention) |
| Migration 0011 roundtrip | upgrade → 0011 on scratch SQLite and scratch PG; 63 → 66 tables; app role grants updated to all 66 tables (264 DML grants) |

## 4. PostgreSQL parity finding fixed in-phase

Athena session/confirmation expiry uses naive-UTC timestamps (the canonical
convention). Scratch PG exposed that a server whose session `TimeZone` is not
UTC (Asia/Kolkata here) silently shifts stored naive values, making a fresh
session appear expired. Fix: every PostgreSQL connection is now pinned to
`SET TIME ZONE 'UTC'` (`backend/app/db/session.py`), making the naive-write →
aware-read round trip exact and identical to SQLite. This also removes the same
latent skew from every other timestamp comparison in the canonical services.
Verified by a full PG flow: register → session → tool call → confirmation →
executed application.

## 5. What is NOT claimed

- No claim that a live LLM behaves safely — the suite proves the *platform*
  refuses, minimizes, and gates regardless of model output.
- No claim of production readiness for a provider (none is configured).
- No claim that conversation contents are purged (no purge job yet).
