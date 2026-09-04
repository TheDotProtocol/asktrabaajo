# Phase 15 — Data Policy

Phase 15 handles professional and preparation data for jobseekers. The policy
follows the platform-wide principles: data minimization, purpose limitation,
least privilege, consent, auditability, retention control and user control.

## What Phase 15 reads

Career Advisor and Interview Preparation read only **canonical structured
data owned by the caller**:

- person profile (professional summary, current position)
- education, work experience, skills
- credentials **with verification state**
- career goals and career milestones
- the caller's own applications (status aggregates + timeline)
- posted opportunity requirements (for gap analysis / question generation)
- public/canonical career-path data

## What never enters Phase 15 context

Deny-list (enforced by the digest builder and asserted by tests):

- government IDs, passport numbers, tax IDs
- KYC state or KYC documents
- document/file contents
- phone numbers, email addresses, home addresses
- private messages, recruiter notes, interviewer assessments
- authentication credentials, passwords, tokens
- employer-private data beyond the caller's own authorized scope

## Credential truthfulness

A credential is presented with its canonical state. The digest never upgrades
an `unverified`/`pending`/`expired`/`revoked` credential to `verified`. The
career paths and recommendations never assert qualifications the candidate has
not actually earned.

## What Phase 15 writes

Only three write paths exist, and every one goes through a canonical service
with explicit authorization:

1. **`career.create_milestone`** (LOW_RISK_WRITE) — creates a milestone on the
   candidate's own account via the canonical milestone service.
2. **Interview-prep session metadata** — status, counters, focus areas, expiry
   (candidate's own session; owner may delete).
3. **`apply_to_opportunities`** (HIGH_RISK_WRITE) — creates applications via the
   canonical application service, gated by the exact-scope confirmation
   framework.

## What Phase 15 never writes

- **Raw answers and mock-interview transcripts are never persisted.**
  Evaluated answers are returned as feedback and discarded. When a mock run
  happens inside an Athena chat, the exchange follows the existing
  sanitized `athena_messages` retention policy.
- No free-form "AI memory" of career conversations is stored anywhere. Career
  state lives in canonical structured data the user controls.

## Retention

| Data | Retention |
|---|---|
| Prep-session metadata | Expires lazily via `expires_at`; owner-deletable; future periodic purge job |
| Raw answers / transcripts | Not stored by default (by design) |
| Athena messages | Existing Phase-14 sanitized-message policy |
| ai_usage_log | Usage accounting only — no content column by construction |

## User control

The candidate controls their profile, goals, visibility, applications and
communications through the canonical platform. Athena assists; it never
silently changes professional identity. Session deletion removes the only
Phase-15-written state (metadata).

## Audit

Audit rows record session/tool/confirmation metadata — never answer content,
never prompt bodies (asserted by test `test_prep_audit_contains_no_answer_content`).
