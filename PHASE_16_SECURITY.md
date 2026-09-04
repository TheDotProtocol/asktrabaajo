# Phase 16 — Security Review

## Entry security

- Session entry uses a random `secrets.token_urlsafe(24)` token returned
  **once** at creation; only its SHA-256 hash is stored. Every candidate
  call carries `X-Interview-Token` and the engine compares hashes with
  `hmac.compare_digest` AND verifies the caller's PersonProfile is the
  session's candidate. A guessed URL is useless; replay needs the token; a
  stolen token still cannot be used by a different person.
- No existence oracle: unknown tokens/sessions return permission/not-found
  errors without distinguishing valid from invalid.

## Tenant isolation

- Employer routes require org membership **and** the `interviews.read` /
  `interviews.manage` permission **and** the session's organization must
  equal the caller's organization (a route-level check was added after the
  adversarial test caught a raw cross-org read).
- Candidate routes are person-scoped by construction.
- Opportunity anchors must belong to the caller's organization; application
  anchors must belong to the selected candidate.
- Tested: employer A → employer B session = 403; candidate A → candidate B
  session/token = 403; concurrent sessions across candidates stay isolated.

## Consent

- Interviews requiring consent cannot start before it is granted (state
  machine: `consent_required` → `ready` only via `grant_consent`).
- Consent snapshot records mic/camera/recording flags + timestamp + version
  (metadata only). Withdrawal transitions to `cancelled` and stops the flow.
- Recording consent defaults to false; no recording capability exists.

## Question safety

- Prohibited-topic gate: employer configuration (competencies,
  introduction/closing) containing protected/private topics is rejected at
  creation; generated questions are re-checked against the gate. Never asked:
  race, religion, politics, sexual orientation, pregnancy, medical
  conditions, disability, age, family planning, financial status, unrelated
  criminal history, appearance, personality inference, and any
  facial/lie-detection framing.
- Follow-ups stay bound to the original competency (`follow_up_of`).

## Data minimization

- The plan grounds only on a whitelisted digest (roles, companies, skills,
  verified credential names) + posted requirements. Government IDs,
  passports, tax IDs, KYC, contact details, private messages and document
  contents are never fetched into the engine.
- **Raw answers are never persisted**: evaluations store dimension scores,
  strengths/improvements and objective evidence markers only. A test scans
  every `ai_interview_*` table for the submitted answer text and asserts its
  absence.

## No privileged AI

- The engine has no SQL/shell/filesystem/HTTP surface; it calls canonical
  services only.
- The model (when configured) cannot mutate state by itself: consent,
  lifecycle and decisions are application actions behind the state machine.
- The employer records the decision; the AI has no code path to
  `decision` fields.

## Rate limiting & audit

- New policies: `ai_interview.create` (20/h), `ai_interview.invite` (20/h),
  `ai_interview.respond` (40/min) — bounded write surface even with a
  compromised token.
- Every lifecycle event, consent, question ask, evaluation, signal, report
  view and decision is audited with action codes and metadata; audit rows
  carry no answer content (asserted by test).

## Capability absence (asserted by tests)

- No route, tool or signal type can express facial analysis, lie detection,
  emotion inference or protected-characteristic inference.
- Autonomous hiring does not exist: decisions are a closed employer-only
  set applied only after completion.

## Test coverage

24 new tests in `tests_phase3/test_ai_interview_phase16.py` — full matrix in
PHASE_16_TESTING.md. No security control was weakened; the full suite
(219 passed / 11 skipped) stays green.
