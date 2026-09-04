# Phase 16 — Migration 0013

One strictly additive migration: `backend/alembic/versions/0013_ai_interview_engine.py`
(71 canonical tables after it).

## Why these four tables (existing tables were inspected first)

- **`interviews`** — real employer/candidate scheduled interview records in
  the pipeline status machine. The AI interview is a distinct orchestration
  domain (consent, entry-token, media, integrity signals, human-decision
  fields); storing it there would corrupt real interview semantics.
- **`athena_sessions` / `athena_messages`** — chat envelopes with a short TTL.
  An interview plan must survive pauses and reconnects and carry employer
  configuration.
- **`interview_prep_sessions`** — candidate-owned *practice* metadata. The AI
  interview is an employer-invited, consent-governed assessment with a
  different tenant model (organization + candidate) and lifecycle.
- No existing table can represent a validated question plan, a per-question
  structured evaluation, or the completion report.

## Tables

### 1. `ai_interview_sessions`
The orchestration envelope: org + candidate person + application/opportunity/
interview anchors (SET NULL), interview type, explicit state machine, media
profile (JSON, provider-neutral), consent snapshot (metadata), SHA-256 entry
token, time fields, bounded integrity signals (JSON), and the employer's
human decision fields. Raw answers, transcripts and media are never stored.

### 2. `ai_interview_questions`
The validated, sequenced plan. Unique `(session_id, sequence)`, category,
competency, difficulty, target skill, reason, suggested dimensions, bounded
follow-ups, and `follow_up_of` (self-FK) for adaptive follow-ups that stay
linked to the parent competency. Cascade with the session.

### 3. `ai_interview_evaluations`
One row per answered question: dimension scores with explanations,
strengths/improvements, objective evidence markers, follow-up marker,
answer length. **No answer-text column exists.**

### 4. `ai_interview_reports`
One per session (unique): summary (human-review-required), competency
evidence, strengths, improvement areas, unanswered areas, integrity signals,
quality metadata. The durable employer-review artifact.

## Constraints, tenancy, RBAC/RLS, audit

- Tenant: organization + candidate person; service/API layer enforces both.
- Entry security: hash of a random token (plaintext never stored).
- RLS: designed for the future stage-B/C groups (owner-read + system-writer
  / platform-role shapes); not enabled in this phase — see
  PHASE_13_RLS_MATRIX.md. The service layer enforces isolation and the
  adversarial tests prove it on SQLite and PostgreSQL.
- Audit: every lifecycle event, consent, question ask, evaluation, signal,
  report view and decision is recorded; no answer content in payloads.
- Retention: lazy expiry + time budget; purge job documented (see
  PHASE_16_DATA_RETENTION.md).

## Validation

| Check | Result |
|---|---|
| SQLite upgrade 0012 → 0013 | clean (72 tables incl. alembic_version) |
| PostgreSQL upgrade 0012 → 0013 | clean (alembic_version 0013) |
| Downgrade 0013 → 0012 → re-upgrade | clean on SQLite **and** PostgreSQL 16 |
| App-role grants after 0013 | 284 = 71 tables × 4 DML |
| Full suite with 0013 applied | 219 passed / 11 skipped / 0 failed (SQLite) |
| PG RLS suite | 11/11 |
| PG end-to-end smoke | PASS |

Migrations 0001–0012 were not modified. No migration was applied to any live
or shared database.
