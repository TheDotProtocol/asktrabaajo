# Phase 16 — AI Interview Engine Architecture

## Position in the platform

Phase 14 built Athena (controlled tools + sessions + confirmations). Phase 15
built the jobseeker preparation layer. Phase 16 adds the **structured AI
interview orchestration system** — an employer-configured, candidate-owned
flow conducted by Athena through deterministic, validated engines. It is not
a chat feature; it is a governed domain with its own lifecycle, consent,
entry security, evaluation and human decision surface.

## System diagram

```
EMPLOYER (authorized org member, interviews.manage)
   ↓  POST /api/v1/ai-interviews   (config: type, competencies, difficulty,
   ↓                                count, media flags, consent policy)
INTERVIEW SESSION (ai_interview_sessions — scheduled)
   ↓  invite → notification + event        entry_token returned ONCE (SHA-256 stored)
CANDIDATE (entry token + person ownership on every call)
   ↓  claim → consent (explicit, per capability) → ready
   ↓  start
ATHENA INTERVIEW ENGINE (services/ai_interview.py)
   ↓  deterministic QUESTION PLAN (ai_interview_questions) grounded in
   ↓  opportunity requirements + candidate Work ID, prohibited-topic-gated
VOICE / VIDEO (provider-neutral media.py abstraction; disabled by default)
   ↓
CANDIDATE RESPONSES (never stored raw)
   ↓  deterministic EVALUATION ENGINE (ai_interview_evaluations,
   ↓  explainable dimensions only)
   ↓  adaptive follow-ups linked to the same competency
COMPLETION → structured REPORT (ai_interview_reports)
   ↓  "AI-assisted assessment. Human review required."
AUTHORIZED EMPLOYER (interviews.read)
   ↓  report + review signals + human DECISION
HUMAN DECISION (advance / reject / hold / follow-up / human interview)
```

Cross-cutting (enforced in code, not by the model):

```
AUTH  →  RBAC (org membership + interviews.*)  →  TENANT (org + person)
     →  CONSENT  →  DATA MINIMIZATION  →  AUDIT  →  EVENTS  →  RATE LIMITS
```

## Domain boundaries

| Concept | Location |
|---|---|
| Orchestration envelope | `ai_interview_sessions` (state machine, consent snapshot, entry-token hash, media profile, signals, decision) |
| Question plan | `ai_interview_questions` (sequenced, validated, persisted for re-entry and audit) |
| Evaluation | `ai_interview_evaluations` (dimensions only — **no raw answer text**) |
| Report | `ai_interview_reports` (summary, competency evidence, quality, review signals) |
| Media | `app/services/media.py` (provider-neutral STT/TTS interface; nothing wired by default) |
| Scheduling/invitations | existing `interviews` records, notification + event services are reused, never duplicated |

## What the model can and cannot do

The model (when a provider is configured) may **adapt and explain** within the
engine's validated structures. It cannot:

- reach the database, filesystem, shell, private storage or arbitrary HTTP
- bypass the session state machine, consent, entry token, or RBAC
- invent evaluation criteria (requirements come from canonical
  `opportunity_requirements` + the skills taxonomy)
- persist answers (there is no storage path for raw responses)
- record audio/video (no recording capability exists)
- make the final employment decision (decision fields are employer-only and
  the report is explicitly human-review-required)

## Explicit non-capabilities

- Facial emotion detection — NOT IMPLEMENTED
- Lie / deception detection — NOT IMPLEMENTED
- Protected-characteristic inference — NOT IMPLEMENTED (prohibited-topic gate)
- Autonomous hiring — NOT IMPLEMENTED (human decision surface only)
- Transcript/recording retention — NOT IMPLEMENTED (governed feature would be
  required first; see PHASE_16_PRIVACY.md)

## Key file map

| File | Purpose |
|---|---|
| `backend/app/models/ai_interview.py` | 4 orchestration tables |
| `backend/app/models/enums.py` | statuses, transitions, types, follow-ups, signals, dimensions, decisions, audit actions |
| `backend/alembic/versions/0013_ai_interview_engine.py` | migration 0013 |
| `backend/app/services/ai_interview.py` | the engine |
| `backend/app/services/media.py` | provider-neutral voice/video abstraction |
| `backend/app/schemas/ai_interview.py` | request/response schemas |
| `backend/app/api/v1/ai_interviews.py` | 19 routes (7 employer + 12 candidate) |
| `frontend/src/app/jobseeker/ai-interview/page.tsx` | candidate lobby/consent/room/completion |
| `frontend/src/app/employer/ai-interviews/page.tsx` | employer list/report/human decision |
