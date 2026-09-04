# Phase 16 — Interview Engine

`backend/app/services/ai_interview.py` implements the orchestration engine
behind the AI interview. Everything below is deterministic application code;
the LLM (when configured) is an optional explainer, never the authority.

## Interview types

`screening`, `behavioral`, `competency`, `role_specific`, `technical`,
`mixed`. Each type maps to a controlled category set for plan generation.

## Session state machine

```
scheduled ──invite──▶ consent_required ──consent──▶ ready ──start──▶ in_progress
   │                     │      │                      │
   │ (employer cancel)   │      │ (consent refused/    │  ┌──────────────┐
   └──────▶ cancelled ◀──┘      │   withdrawn)         ▼  ▼              │
            │                   └─────────────────▶ cancelled     paused ◀┘
            │                      expired (lazy)   (any pre-start)   │ resume
            ▼                                                        ▼
         expired ◀──────────────────────────────────────────── in_progress ──▶ completed
                                                          (time budget /        │
                                                           exhausted, or       │
                                                           candidate finish)    │
                                                                                ▼
                                                          cancelled (consent    │
                                                           withdrawn mid-flow)  │
                                                                                ▼
                                                         failed (terminal       │
                                                          media/provider)       │
```

Transitions are explicit (`AI_INTERVIEW_TRANSITIONS`); impossible transitions
raise instead of silently mutating. Every transition is audited.

## Deterministic lazy expiry

- `expires_at` (7-day invite window) hard-expires pre-start sessions without
  any scheduler.
- A live session past its invite window but inside its time budget is not
  killed mid-flow.
- The time budget (`started_at + duration_minutes`) ends the interview
  gracefully on the next question fetch or response — a scheduled end, not a
  crash. Completeness/quality metadata records how far the candidate got.

## Question plan

Generated at `start` (once, persisted so the plan survives pauses and
reconnects):

1. Reduce the candidate's own professional digest to whitelisted grounding
   fields (roles, companies, skills, verified credentials).
2. Load the posted opportunity's requirements verbatim from
   `opportunity_requirements`.
3. Build candidate questions per interview type from controlled banks,
   grounded in the configured competencies, the requirements and the
   candidate's real history.
4. **Prohibited-topic gate** — any question matching the protected/private
   topic patterns is dropped; employer configuration that contains such
   topics is rejected at creation.
5. Persist sequenced rows (category, competency, difficulty, target skill,
   reason, suggested dimensions, bounded follow-ups).

## Adaptive follow-ups

Follow-ups are persisted rows with `follow_up_of` pointing at the parent
question, keeping them bound to the same competency. Rule: a parent question
answered with low evidence (evidence score ≤ 2) whose follow-up budget is not
exhausted yields a linked follow-up next (evidence/example/depth/technical
detail depending on category). Bounded at 3 follow-ups per session. Follow-up
budgets mean one answer can never consume the whole interview.

## Question repeat

Candidates may ask to repeat a question; the engine rephrases it and records
an audit event. Repeats are never an evaluation penalty and never create an
evaluation row.

## Evaluation engine

Deterministic scoring of job-relevant dimensions (relevance, clarity,
structure, evidence, completeness, role knowledge, technical accuracy,
problem solving, communication — selected per category). Scores (1–5) carry
one-line explanations; strengths/improvements are derived from them; only
objective evidence markers are recorded. **No raw answer text is stored
anywhere** (asserted by a test that scans every interview table).

## Reports

On completion the engine writes one report row: summary (explicitly
human-review-required), competency evidence grouped by competency,
strengths/improvement areas, unanswered areas, integrity signals (labeled
review signals), and quality metadata (answered/total, completion %, average
dimension score with an explicit "not a hiring probability" note).

## Employer decision

After completion an authorized employer records a decision from a closed set:
`advance`, `reject`, `hold`, `request_followup`, `request_human_interview`.
The AI has no path to these fields.

## Integrity signals

Candidate/UI-reported objective events (`session_disconnect`,
`session_reconnect`, `unexpected_termination`, `mic_state_changed`,
`camera_state_changed`, `session_duplicate`), bounded at 50 per session,
audited, and surfaced in the report as **review signals** — never as
penalties and never as proof of wrongdoing.
