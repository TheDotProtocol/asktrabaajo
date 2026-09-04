# Phase 15 — Jobseeker Career Advisor + AI Interview Preparation

**Project:** AskTrabaajo / Trabaajo 2.0 · **AI:** Athena
**Status:** COMPLETE — see status block at the end.

---

## 1. Objective

Turn the Phase 14 Athena foundation into the first genuinely useful jobseeker
product surface. Two capabilities were delivered:

1. **Career Advisor** — a deterministic, explainable intelligence layer over the
   candidate's own Work ID: profile digest, skill-gap analysis, career paths,
   opportunity recommendations, application analysis and suggestion-only action
   plans.
2. **AI Interview Preparation** — structured question generation and mock-answer
   evaluation that never leaves the candidate's control and never retains raw
   answers.

Both capabilities reuse the Phase 14 Athena controls: registered tools, mode and
permission gates, confirmation for high-risk actions, context minimization,
audit, rate limits and usage accounting. **No Phase 14 control was weakened.**

The full autonomous AI interviewer, live interview engine and Career Advisor
"chat persona" beyond the Athena tool surface were **not** built — they remain
later-phase work.

## 2. Starting state (verified)

- Canonical schema: **66 tables**, migrations 0001–0011.
- Canonical routes: **200** `/api/v1` (Phase 14 added 8 Athena routes).
- Athena: 26 controlled tools, provider abstraction, sessions, confirmation
  framework, `ai_usage_log` accounting.
- Tests: 177 passed / 11 skipped (SQLite), 11 PostgreSQL RLS tests passing
  separately; legacy Careers backend intact at 107 routes.
- Git HEAD `315d684` (Phase 14). Live Supabase never touched — direct SQL
  credentials remain unavailable (Phase 13 blocker, unchanged).

## 3. Architecture impact

```
                ASKTRABAAJO
                     │
                   ATHENA (Phase 14 core, unchanged)
                     │
        ┌────────────┴────────────┐
        │                         │
  CAREER ADVISOR            INTERVIEW PREP
  (deterministic domain)    (deterministic domain)
        │                         │
        └────────────┬────────────┘
                     │
         registered Athena tools (13 new, 39 total)
                     │
              CANONICAL SERVICES
                     │
         authorization / tenant / consent
                     │
                   AUDIT
```

New deterministic services (`app/services/career_advisor.py`,
`app/services/interview_prep.py`) sit **below** Athena and are also callable
directly by the REST API and the frontend. Athena can only reach them through
registered tools carrying explicit modes, permissions, data scope and risk.

## 4. Career Advisor

Implemented in `app/services/career_advisor.py`, exposed at
`/api/v1/career-advisor/*` and via seven registered Athena tools.

- **Profile digest** — whitelisted professional summary: current position,
  experience/education summaries, credentials with their verification state,
  skills, career goal, milestones, application status counts. No contact
  details, no government/tax/passport fields, no document contents.
- **Skill-gap analysis** — deterministic comparison of the candidate's skills
  against one posted opportunity (or their career goal): matched / partial /
  missing skills, coverage percentage, experience and credential gaps.
  Requirements come only from canonical `opportunity_requirements` and the
  skills taxonomy; the LLM cannot invent requirements.
- **Career paths** — advisory steps from the canonical career-path
  infrastructure, classified by the candidate's *held history* versus *stated
  goal* (DIRECT / ADJACENT / TRANSITION / EXPLORATORY). Never presented as a
  guaranteed outcome.
- **Opportunity recommendations** — explainable recommendations in the four
  canonical matching modes (strong / potential / transition / explore), each
  with explicit reason factors from structured platform signals.
- **Application analysis** — deterministic read of the candidate's own
  application history: counts by status, response patterns, nothing about other
  candidates, no employer-private content.
- **Action plan** — suggestion-only milestones derived from the Work ID and
  goal; nothing is executed or persisted as an obligation.

## 5. Interview Preparation

Implemented in `app/services/interview_prep.py` and the
`interview_prep_sessions` table (migration 0012), exposed at
`/api/v1/interview-prep/*` and via five registered Athena tools.

- **Sessions** — candidate-owned metadata containers (opportunity / application
  / interview / Athena-session anchors optional). Active, completed and expired
  states; deterministic lazy expiry via `expires_at`; owner can delete at any
  time. A session row records only *that a flow existed* and its focus — **raw
  questions and answers are never persisted** (see DATA_POLICY).
- **Question generation** — deterministic, structured questions in six
  categories (behavioral, technical, role_specific, competency, situational,
  career_history). Each question carries category, competency, difficulty,
  reason, target skill and suggested answer dimensions, grounded in the posted
  role requirements and the candidate's real Work ID.
- **Answer evaluation** — deterministic feedback on job-relevant dimensions
  (relevance, structure, evidence, completeness, role knowledge), plus
  "what you did well / what was missing / how to improve / a pointer toward a
  stronger response" and an explicit disclaimer that this is preparation
  feedback, not a hiring prediction. No protected-characteristic inference, no
  emotion/lie-detection, no opaque hireability score.
- **Mock-interview flow** — question → answer → evaluation → next question over
  the session, text-based only. When run inside Athena, the exchange lives in
  the existing sanitized `athena_messages` flow under Phase-14 retention rules.

## 6. Athena tool extension (26 → 39)

| Tool | Risk | Notes |
|---|---|---|
| `career.get_profile_digest` | READ_ONLY | own digest |
| `career.get_skill_gaps` | READ_ONLY | vs one opportunity / goal |
| `career.get_career_paths` | READ_ONLY | advisory, classified |
| `career.get_recommendations` | READ_ONLY | explainable, 4 modes |
| `career.get_application_analysis` | READ_ONLY | own history only |
| `career.get_action_plan` | READ_ONLY | suggestion-only |
| `career.create_milestone` | LOW_RISK_WRITE | via canonical milestone service |
| `interview.start_prep_session` | LOW_RISK_WRITE | creates candidate-owned session |
| `interview.get_questions` | READ_ONLY | deterministic generation |
| `interview.submit_answer` | LOW_RISK_WRITE | evaluation only; nothing stored |
| `interview.complete_prep_session` | LOW_RISK_WRITE | closes a session |
| `interview.get_prep_session` | READ_ONLY | own session only |
| `apply_to_opportunities` | HIGH_RISK_WRITE | bulk apply — exact-scope confirmation |

All 13 new tools are jobseeker-mode only. Employer/recruiter mode cannot reach
any of them (enforced by mode gate **and** by the permission layer, tested).

## 7. High-risk actions — bulk apply

`apply_to_opportunities` never executes on a model instruction. It:
1. validates the candidate identity and each opportunity,
2. computes an exact canonical scope (sorted opportunity UUIDs + candidate id),
3. stores a single-use, 15-minute confirmation whose payload is a SHA-256 digest
   of that canonical scope (raw opportunity lists are not persisted),
4. on approval re-loads and re-authorizes each opportunity **at approval time**,
   so a changed opportunity set after confirmation never matches, and
5. creates applications through the canonical application service with full
   audit, then records the confirmation result.

## 8. API routes (200 → 213)

`/api/v1/career-advisor`: `GET digest`, `GET gaps`, `GET paths`,
`GET opportunities` (mode/limit), `GET applications`, `GET action-plan`.

`/api/v1/interview-prep`: `POST sessions`, `GET sessions`,
`GET sessions/{id}`, `POST sessions/{id}/questions`,
`POST sessions/{id}/answers`, `POST sessions/{id}/complete`,
`DELETE sessions/{id}`.

All routes resolve the caller's PersonProfile server-side; no route accepts
another person's id, and the owner check is enforced in the service layer (404
for non-owners, tested on SQLite and PostgreSQL).

## 9. Database change (migration 0012)

One additive table: **`interview_prep_sessions`** (67 canonical tables now).

- **Why a new table:** a session container is real state (status, expiry,
  counters, focus, anchors). No existing table represents a candidate-owned
  preparation flow; `athena_sessions` is chat-scoped and governed by Athena
  retention, and persisting prep state there would conflate domains.
- **What it deliberately does NOT store:** questions, answers, transcripts.
  Those are computed at request time and (in the Athena path) live under the
  sanitized Athena-message retention policy.
- Person-owned (`person_id` FK, cascade), optional anchors to
  opportunity/application/interview/athena_session (SET NULL), status, JSON
  `focus_areas`, counters, `last_activity_at`, `expires_at`, `completed_at`.
  Idempotent `DO`-block-free standard migration; downgrade drops the table;
  validated upgrade → downgrade → re-upgrade on SQLite and PostgreSQL 16.
- Runtime grants extended: `scripts/db/app_role.sql` now covers 67 tables
  (268 DML grants verified on scratch PG).

## 10. Frontend

- `frontend/src/lib/api/types.ts`: Phase-15 API response types.
- `frontend/src/app/jobseeker/interview-prep/page.tsx`: new functional page —
  start a session, generate questions, answer, get structured feedback,
  complete/delete.
- `frontend/src/app/jobseeker/layout.tsx`: "Interview Prep" nav entry.
- The existing `/jobseeker/career` surface remains the Career Advisor UI home.
- **Typecheck clean, lint clean (exit 0; only pre-existing warnings in carried
  Careers files), production build green** (`/jobseeker/interview-prep` in the
  route manifest).

## 11. PostgreSQL validation (scratch PG 16, never live)

- Migration 0012 upgrade + downgrade roundtrip clean; `alembic_version` 0012,
  68 public tables (67 canonical + alembic_version).
- App-role grants re-ran: 268 = 67 tables × 4 DML privileges.
- RLS suite: **11/11 pass** on PG with migration 0012 present.
- End-to-end PG smoke (`PG_SMOKE_PASS`) over the real app engine: register →
  career digest/gaps/paths → prep session create → questions → answer
  evaluation → complete → cross-user 404 isolation → owner delete. The
  UTC-pinning session event (Phase 14) keeps naive-UTC round-trips consistent
  on `timestamptz` columns.

## 12. Security results

- 18 new adversarial/deterministic tests (see PHASE_15_EVALUATION.md for the
  full matrix): cross-user digest isolation, auth requirement, matched/partial/
  missing gap accuracy, direct vs transition path classification, employer
  blocked from career/prep tools, fabrication prompts yielding no tool call,
  exact-scope bulk-apply confirmation (wrong object / changed set / expiry),
  prep-answers-never-persisted, lazy expiry, audit rows free of answer content.
- No weakening of Phase 14 controls; all existing tests preserved.

## 13. Test counts

| Suite | Passed | Failed | Skipped |
|---|---|---|---|
| Canonical backend (SQLite, tests_phase3) | **195** | 0 | 11 (PG-only RLS, by design) |
| PostgreSQL RLS suite | **11** | 0 | 0 |
| New Phase-15 tests | **18** | 0 | 0 |

Frontend: typecheck PASS · lint PASS · production build PASS.
Routes: canonical **213** · legacy backend **107** (unchanged).
Athena tools: **39**.

## 14. Legacy compatibility

Legacy Careers backend untouched by Phase 15 (imports cleanly at 107 routes).
No legacy file was modified. The 63 carried Phase-1 hygiene working-tree
entries remain untouched and uncommitted.

## 15. Known limitations

- Career Advisor is deterministic-intelligence + Athena tool surface; the
  conversational "where should I go next" persona beyond tool calling is Phase
  16+ product work.
- Prep session rows persist (metadata only); a retention purge job is a
  documented follow-up (lazy expiry already bounds correctness without one).
- Live provider credential still unavailable → Athena remains in safe degraded
  mode (`ai.provider_unavailable`), unchanged from Phase 14.
- Live Supabase deployment still blocked on the Phase 13 credential issue.

---

## PHASE 15 STATUS:
PASS WITH LIMITATIONS

CAREER ADVISOR:
IMPLEMENTED

CAREER PROFILE DIGEST:
PASS

CAREER GAP ANALYSIS:
PASS

CAREER PATHS:
PASS

OPPORTUNITY INTELLIGENCE:
PASS

APPLICATION ANALYSIS:
PASS

AI INTERVIEW PREPARATION:
IMPLEMENTED

MOCK INTERVIEW:
IMPLEMENTED

AI SAFETY:
PASS

DATA MINIMIZATION:
PASS

AUTHORIZATION:
PASS

AUDIT:
PASS

NEW TABLES:
interview_prep_sessions — candidate-owned preparation-session metadata
container (status/expiry/counters/anchors); raw questions and answers are
never stored, so no question/answer tables were justified.

NEW MIGRATIONS:
0012_interview_prep — adds interview_prep_sessions (additive, downgrade tested)

TESTS:
195 PASSED (SQLite canonical) + 11 PASSED (PostgreSQL RLS) = 206
0 FAILED
11 SKIPPED (PG-only RLS under SQLite, by design)
0 BLOCKED

LIVE SUPABASE:
NOT TOUCHED

FRONTEND:
INTEGRATED

PRODUCTION READINESS:
DEVELOPMENT READY (staging deployment blocked on the Phase 13 credential
issue; no live-provider AI credential configured)

BLOCKERS:
1. Live Supabase SQL credentials unavailable (Phase 13 blocker, unchanged) —
   no live migration/RLS/deployment executed.
2. No live AI provider credential — Athena runs in safe degraded mode until an
   OPENAI_API_KEY (or equivalent) is provisioned server-side in staging.
3. Prep-session metadata retention purge job not yet implemented (correctness
   does not depend on it — lazy expiry is deterministic).

PHASE 16 RECOMMENDATION:
1. Career Advisor conversational product layer on the existing tool surface
   (digest → paths → opportunities → action plan in one Athena thread) once a
   staging provider credential exists.
2. Athena message retention purge job + prep-session expiry cleanup worker.
3. Execute the Phase 13 deployment runbook (0010 RLS groups B/C staged on live)
   when SQL credentials land, then wire frontend to the live canonical API.
4. Full AI Interviewer / interview product (audio/video, live flow) remains a
   separate later phase built on the same controlled foundation.
