# CURSOR WAVE 4 CLOSURE — Athena UI

**Status:** IMPLEMENTED (local, unpushed)  
**Depends on:** Wave 3 IMPLEMENTED  
**Figma:** none — designed from Candidate/Employer OS (`CURSOR_ATHENA_DESIGN_DECISIONS.md`)  
**Hosted database:** **UNTOUCHED**

Athena is now a real client of `/api/v1/athena/*` inside both operating systems. Waves 1–3 were not replaced. Wave 5 was not started.

## 1. Implemented

- Shared `AthenaWorkspace` (conversation, context rail, starter prompts, degraded state)
- Candidate Athena at `/jobseeker/athena`
- Employer Athena HR at `/company/athena`
- Contextual `?from=` + Ask Athena links
- Structured result cards
- Exact-scope confirmation dialog
- Honest `AI_PROVIDER=none` degraded mode
- `GET /athena/status` (no secrets)

## 2. APIs

Existing Athena routes plus status. No mock `/api/chat`. No frontend AI engine.

## 3. Backend changes

One route: `GET /athena/status` → `{ available, state, modes }`.

## 4. Database

No migrations. No hosted writes. Isolated sqlite E2E.

## 5. Security tests

`scripts/wave4_athena_e2e.py`: degraded chat, mode isolation, cross-tenant session, stolen session, unknown confirmation, unauthenticated access.

Phase 14 remains the confirmation SHA-256 / expiry / reuse suite.

Wave 2 and Wave 3 E2E re-run as regression.

Quality: `tsc` PASS · lint 0 errors (5 pre-existing Careers warnings) · `next build` PASS · `pytest tests_phase3` PASS (251 sqlite + 11 RLS on local `p14_test` when `TEST_PG_URL` is set).

## 6. Remains

- Persistent Athena history (no list API)
- Live provider provisioning
- Recruiter-specific chrome (same employer tools)
- Government Athena product
- Public website CTAs

## 7. Blocked

Real OpenAI credentials, production deploy, push, autonomous hiring (forbidden).

## 8. Wave 5

Ready as a **separate** approval: communications/governance polish per `CURSOR_WAVE_5_READINESS.md`.

---

## 9. Refinement pass

Focused Athena quality pass after Wave 4 acceptance. **Not Wave 5.** No backend rewrite. No hosted DB writes. No deploy/push.

### UI refinements

Identity → context band → conversation → structured cards → named actions → exact confirmation. Context rail no longer dominates. Mobile uses chips instead of a stacked desktop rail.

### Candidate vs Employer

Shared `AthenaWorkspace`. Different first-use copy, starters, and OS destinations.

### Contextual behaviour

Allowlisted `?from=` preserved. New Ask Athena links: Applications, Interviews, Work ID, Jobs, Employer Interviews.

### Degraded state

Polished unavailable hero. Composer stays closed when `AI_PROVIDER=none`. No fabricated replies.

### Confirmation UX

Dialog title is the human action and count. Consequence copy is tool-specific. Focus trap + Escape. Backend `POST /athena/confirm` is still the security boundary.

### Responsive / a11y

Dedicated mobile sheet confirmation, no horizontal overflow, `aria-live` phase announcements, labelled composer and Ask Athena links.

### Backend / database

No additional backend change. Hosted DB **UNTOUCHED**.

### Tests

Re-run Wave 2, Wave 3, Wave 4 E2E; `pytest tests_phase3`; frontend `tsc` / lint / build.
