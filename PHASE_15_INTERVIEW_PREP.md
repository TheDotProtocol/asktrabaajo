# Phase 15 — AI Interview Preparation

Interview Preparation is the **preparation layer only**. It generates
structured practice questions, evaluates the candidate's written answers on
job-relevant dimensions, and gives improvement feedback. It is not a live AI
interviewer, and it never makes or influences an actual hiring decision.

## Session model

`interview_prep_sessions` (migration 0012) is a **candidate-owned metadata
container**. One row per preparation flow, owned by `person_id` (cascade
delete). Optional anchors to the opportunity, application, real interview or
Athena chat the candidate is preparing for (`SET NULL` on delete).

The row records:
- status: `active` → `completed` | `expired` (lazy, deterministic via
  `expires_at`)
- JSON `focus_areas` (the candidate's own bounded, sanitized focus)
- counters: `questions_generated`, `answers_evaluated`
- `last_activity_at`, `expires_at`, `completed_at`

**Raw questions and answers are never persisted.** Questions are generated at
request time; evaluated answers return feedback and are discarded. When a mock
run happens inside an Athena conversation, the exchange lives in
`athena_messages` under the existing sanitized-message retention policy.
This is a deliberate data-policy decision (see PHASE_15_DATA_POLICY.md).

## Question generation

Deterministic and structured. Generation draws on:

- the posted opportunity's requirements (when the session is anchored to one),
- the candidate's real Work ID (skills, experience, education, credentials) so
  `career_history` questions ground in the candidate's actual narrative,
- a canonical prompt bank per category.

Six categories: `behavioral`, `technical`, `role_specific`, `competency`,
`situational`, `career_history`. Each question carries:

- `question`, `category`, `competency`, `difficulty` (easy/medium/hard)
- `reason` (why this question is useful)
- `target_skill`
- `suggested_answer_dimensions`

A `note` on every generated set reminds the candidate that these are practice
questions and the employer may ask different ones.

## Answer evaluation

Deterministic feedback over explainable, job-relevant dimensions. The dimension
set is category-aware (e.g. technical questions score `role_knowledge`,
behavioral questions weight `structure` and `evidence`), always including
relevance, structure, evidence and completeness. Feedback contains:

- per-dimension scores with one-line explanations
- what you did well (top strengths)
- what was missing (top improvements)
- how to improve (targeted guidance)
- a pointer toward a stronger response shape (never fabricated experience)

Every evaluation ends with the disclaimer that this is preparation feedback —
**not** a prediction of interview success or hiring.

Explicitly **not** evaluated or inferred: protected characteristics, emotion,
facial analysis, lie detection, psychological state, "hireability".

## Mock interview flow

Text-based, candidate-driven:

1. `POST /sessions` — create a session (optionally anchored to an
   opportunity/application/interview, with focus areas).
2. `POST /sessions/{id}/questions` — generate a practice set (count 1–10,
   optional category filter).
3. `POST /sessions/{id}/answers` — submit an answer; receive structured
   evaluation.
4. Repeat; `POST /sessions/{id}/complete` closes the session.
5. `DELETE /sessions/{id}` — candidate deletes the session at any time;
   `GET /sessions` / `GET /sessions/{id}` list/lookup own sessions.

## Ownership and isolation

Every service call resolves the caller's PersonProfile server-side and the
session must belong to that person (404 otherwise). Non-owners cannot read,
answer, complete or delete a session — enforced in the service layer and
regression-tested on both SQLite and PostgreSQL.

## Athena integration

Five Athena tools (jobseeker mode only): `interview.start_prep_session`,
`interview.get_questions`, `interview.submit_answer`,
`interview.complete_prep_session`, `interview.get_prep_session`. All are
READ_ONLY or LOW_RISK_WRITE (they mutate only the candidate's own session
metadata); none can touch an employer's data or a real interview record.

## Retention

- Session metadata rows expire lazily and can be deleted by their owner.
- Raw narrative answers are never stored anywhere by default.
- Future work: a periodic purge job for expired session rows (correctness does
  not depend on it).
