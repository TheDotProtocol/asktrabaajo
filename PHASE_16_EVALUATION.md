# Phase 16 — Evaluation Model

## What is evaluated

Interview answers are evaluated deterministically on **job-relevant,
explainable dimensions**. The dimension set is chosen per question category:

| Dimension | Meaning |
|---|---|
| relevance | Answer engages the question's subject |
| clarity | Readable, low filler |
| structure | Ordered / STAR-style narrative markers |
| evidence | Concrete, measurable outcome markers |
| completeness | Depth for a spoken response |
| role_knowledge | Connection to the role's domain |
| technical_accuracy | Correct technical vocabulary |
| problem_solving | Visible reasoning chain |
| communication | Clear, well-paced delivery |

Each dimension is scored 1–5 **with a one-line explanation**. There is no
single opaque "AI score": the report surfaces per-dimension evidence,
strengths and improvement areas, plus quality metadata (answered/total,
completion %, average dimension score) whose note states explicitly that it
is **not a hiring probability**.

## What is never evaluated or inferred

- Protected characteristics (race, religion, gender, age, pregnancy,
  disability, sexual orientation, political affiliation, …)
- Facial emotion, facial personality, attractiveness
- Lie / deception detection from any signal
- Medical or psychological state
- "Hireability"

These capabilities do not exist in code. The question engine has a
prohibited-topic gate that rejects config and questions touching them, and
the test suite asserts no route or signal type can express facial/lie/
emotion concepts.

## Evidence markers

Only **objective markers** are recorded on an evaluation row (e.g. presence
of metrics/outcome language, STAR markers). Raw answers are not stored, so
evaluation rows never become a transcript by accident.

## Report structure

`ai_interview_reports` stores: a summary explicitly marked
human-review-required; `competency_evidence` grouped by competency (with
evidence markers and evidence scores); `strengths` and `improvement_areas`
derived from per-answer evaluations; `unanswered_areas` (plan questions the
candidate never answered); integrity signals labeled review signals; and
`interview_quality` metadata.

## Integrity signals are not evaluations

Signals (disconnect, reconnect, termination, mic/camera state, duplicate
session) are objective events stored on the session, bounded, audited, and
surfaced in the report with the label "REVIEW SIGNAL — not proof of
wrongdoing". They never adjust a dimension score. A session with many
signals may warrant human follow-up; it can never auto-reject a candidate.

## Quality vs. penalty

Technical problems (provider outage, disconnect, mic failure) are handled by
the engine as quality signals and recovery paths (retry / repeat / resume) —
they are never converted into candidate performance penalties, and the
engine's test suite pins this down.
