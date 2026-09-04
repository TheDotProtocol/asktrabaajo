# Phase 16 — AI Interview Engine / Live AI Interviewer

**Project:** AskTrabaajo / Trabaajo 2.0 · **AI:** Athena
**Status:** COMPLETE — see status block at the end.

## 1. Objective

Turn the Phase 14 Athena foundation and the Phase 15 preparation layer into a
production-grade interview orchestration system: an employer configures an
interview for a candidate, the candidate enters a secure session with
explicit consent, Athena conducts a structured interview through a
deterministic, validated engine, and the employer receives an AI-assisted
report and makes the **human** decision.

Athena assists with interviewing and evaluation. Athena does **not** make the
final hiring decision.

## 2. Starting state (verified)

- 67 canonical tables (migrations 0001–0012); 213 `/api/v1` routes;
  195 passed / 11 skipped / 0 failed (SQLite); 11 PG RLS tests; 39 Athena
  tools; legacy backend at 107 routes.
- Git HEAD `f1ff801`; live Supabase untouched (SQL credentials still
  unavailable — Phase 13 blocker).

## 3. Architecture impact

New domain below Athena, reusing the canonical service/audit/event/
notification/rate-limit infrastructure:

```
EMPLOYER → config (interviews.manage) → ai_interview_sessions
  → invite/notification/event → CANDIDATE (entry token + person check)
  → consent → start → deterministic question plan (grounded, gated)
  → answers (never stored raw) → evaluation engine → adaptive follow-ups
  → completion → structured report (human-review-required)
  → EMPLOYER report + review signals → human decision (closed set)
```

19 new routes under `/api/v1/ai-interviews` (7 employer, 12 candidate) —
213 → **232**. New rate-limit policies; new audit actions; new event types.
Four new tables (migration 0013). Provider-neutral voice/video abstraction
(`media.py`) with no production provider wired — voice/video are mocked and
safe-degraded by default.

## 4. Engine highlights

- **State machine** — scheduled → consent_required → ready → in_progress ↔
  paused → completed/cancelled/expired/failed; impossible transitions raise;
  every transition audited; deterministic lazy expiry and a time budget (no
  scheduler dependency).
- **Entry security** — random token returned once; SHA-256 stored; hash
  compare + person-ownership check on every candidate call; no existence
  oracle.
- **Consent** — explicit per capability (mic/camera/recording), snapshot
  stored, withdrawal stops the session.
- **Question plan** — deterministic, grounded in posted requirements +
  candidate Work ID digest, prohibited-topic-gated (protected
  characteristics and unrelated sensitive topics can never be asked;
  employer config touching them is rejected).
- **Adaptive follow-ups** — persisted rows bound to the parent competency
  (`follow_up_of`), budgeted at 3/session, triggered only by low-evidence
  answers.
- **Evaluation** — explainable 1–5 dimension scores with explanations;
  strengths/improvements/evidence markers only; **raw answers never
  persisted** (test scans every interview table).
- **Reports** — summary, competency evidence, strengths, improvement areas,
  unanswered areas, integrity signals labeled review signals, quality
  metadata with an explicit "not a hiring probability" note, and an
  "AI-assisted assessment. Human review required." disclaimer.
- **Human decision** — employer-only closed set (advance/reject/hold/
  request_followup/request_human_interview) after completion; no AI path.
- **Capability absence** — no facial emotion analysis, no lie detection, no
  protected-characteristic inference, no recording, no autonomous hiring.

## 5. Migration (0013)

Strictly additive: `ai_interview_sessions`, `ai_interview_questions`,
`ai_interview_evaluations`, `ai_interview_reports` (each justified in
PHASE_16_MIGRATION.md). Roundtripped on SQLite and PostgreSQL 16; app-role
grants extended to 71 tables (284 privileges verified).

## 6. Frontend

- `/jobseeker/ai-interview` — candidate lobby (token entry), consent,
  start (with explicit "I am an AI interviewer" disclosure), question flow,
  feedback, repeat/pause/resume/finish, withdrawal; nav entry added.
- `/employer/ai-interviews` — org picker from memberships, session list,
  structured report, integrity signals, and the human decision buttons.
- API client extended to pass `X-Interview-Token`; Phase-16 types added.
- Typecheck clean · lint clean (no new warnings) · production build green.

## 7. Test results

- **219 passed / 11 skipped / 0 failed** on SQLite (24 new Phase-16 tests).
- **11/11 RLS tests** pass on PostgreSQL with migration 0013.
- PG end-to-end smoke **PASS** (create → invite → claim → consent → start →
  answers → complete → report → decision → cross-org 403).
- Frontend green; legacy backend imports at 107 routes (untouched).

## 8. Known limitations

- Voice/video: architecture + mocks only; no production STT/TTS/WebRTC
  provider wired (safe-degraded `ai.media_unavailable`), consistent with the
  Phase 14 provider stance.
- Live Supabase deployment still blocked on the Phase 13 credential issue;
  nothing live was touched.
- Transcript/recording features intentionally do not exist; governed design
  documented in PHASE_16_PRIVACY.md / PHASE_16_DATA_RETENTION.md.
- Retention purge job documented, not implemented (correctness does not
  depend on it).

---

## PHASE 16 STATUS:
PASS WITH LIMITATIONS

AI INTERVIEW ENGINE:
IMPLEMENTED

INTERVIEW CONFIGURATION:
PASS

CANDIDATE SESSION:
PASS

CONSENT:
PASS

QUESTION ENGINE:
PASS

ADAPTIVE FOLLOW-UP:
PASS

VOICE:
MOCKED

VIDEO:
MOCKED

EVALUATION:
PASS

EMPLOYER REPORT:
PASS

CANDIDATE PRIVACY:
PASS

EMPLOYER PRIVACY:
PASS

INTEGRITY SIGNALS:
PASS

FACIAL EMOTION DETECTION:
NOT IMPLEMENTED

LIE DETECTION:
NOT IMPLEMENTED

PROTECTED CHARACTERISTIC INFERENCE:
NOT IMPLEMENTED

AUTONOMOUS HIRING:
NOT IMPLEMENTED

AUDIT:
PASS

SECURITY:
PASS

NEW TABLES:
1. ai_interview_sessions — orchestration envelope (state machine, consent
   snapshot, entry-token hash, media profile, integrity signals, human
   decision). Existing interview/athena/prep tables cannot represent this
   domain without corrupting real interview or chat semantics.
2. ai_interview_questions — validated, sequenced plan with adaptive
   follow-ups (follow_up_of); persisted for re-entry, audit and the report.
3. ai_interview_evaluations — structured dimension evaluations with NO
   answer-text column (raw answers are never persisted).
4. ai_interview_reports — the durable AI-assisted report artifact, uniquely
   per session, marked human-review-required.

NEW MIGRATIONS:
0013_ai_interview_engine (additive; upgrade/downgrade/re-upgrade validated on
SQLite and PostgreSQL 16)

LIVE SUPABASE:
NOT TOUCHED

TESTS:
219 PASSED (SQLite canonical) + 11 PASSED (PostgreSQL RLS) = 230
0 FAILED
11 SKIPPED (PG-only RLS under SQLite, by design)
0 BLOCKED

FRONTEND:
INTEGRATED

PRODUCTION READINESS:
DEVELOPMENT READY (staging deployment blocked on the Phase 13 credential
issue; voice/video providers not wired)

BLOCKERS:
1. Live Supabase SQL credentials unavailable (Phase 13 blocker, unchanged) —
   no live migration/RLS/deployment executed.
2. No production STT/TTS/WebRTC provider configured — voice/video remain
   architecture-only mocks by design until providers are provisioned.

OWNER ACTIONS:
1. Provide the current pooler connection string + password for
   zrvrjqwboylvvzusorry (Supabase dashboard) so the Phase 13 deployment
   runbook (0010 RLS groups B/C staged on live) can be executed.
2. Rotate the known-exposed credentials from the Phase 1 backlog.
3. Confirm Supabase backup/PITR status before any live migration.
4. When a voice provider is desired, provision server-side STT/TTS
   credentials (never in source) and wire provider adapters behind
   AI_STT_PROVIDER / AI_TTS_PROVIDER.

PHASE 17 RECOMMENDATION:
1. Run the Phase 13 deployment runbook on the live project once credentials
   land (migrations 0001–0013, app role, staged RLS).
2. Employer hiring-pipeline integration: surface AI-interview sessions and
   reports in the employer job/application pipeline and feed decisions into
   application status transitions via the canonical state machine.
3. Career Advisor conversational product layer (Phase 15 recommendation) on
   the Athena tool surface with a staging provider credential.
4. Full AI Interviewer product extensions (real voice transport, governed
   transcript feature, scheduling/calendar integration) behind the controls
   this phase established.
