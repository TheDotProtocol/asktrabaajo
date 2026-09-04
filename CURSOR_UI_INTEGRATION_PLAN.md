# CURSOR UI INTEGRATION PLAN

**Objective:** connect the existing AskTrabaajo UI to the canonical backend (`/api/v1`, `frontend/src/lib/api/`) **without redesigning the platform architecture**. Backend, DB, RBAC, AI, and commerce controls are complete — UI integration only. Read `CURSOR_HANDOFF.md` + `CURSOR_DO_NOT_BREAK.md` first.

**Guiding facts:** 246 canonical routes (see `API_CONTRACT.md`); canonical client exists (`src/lib/api/{client,session,types}.ts`, already used by 29 page files); dual-auth gap (login/register still write legacy sessions); gaps catalogued in `FRONTEND_GAP_REPORT.md`; test/verify against `pytest tests_phase3` + `npx tsc --noEmit && npx eslint src && npm run build`.

---

## WAVE 1 — FRONTEND FOUNDATION (do this first; everything depends on it)

| Item | Detail |
|---|---|
| API base config | `NEXT_PUBLIC_API_URL` in `.env` (see `.env.example`); client already reads it |
| **Auth bridge (critical)** | Login/register pages must call `lib/api/session.ts#login/register` and `setSession()` so canonical tokens exist after login. Retire `useAuth` for canonical surfaces (keep only for legacy/careers pages) |
| Session persistence | Canonical tokens in localStorage today; move access token to memory with refresh-token rotation via `POST /auth/refresh`; wire `ApiClient.onUnauthorized` to refresh-then-retry |
| Logout | `POST /auth/logout` + `clearSession()` in shared nav |
| Route guards | Shared guard component: no token → redirect to `/login`; role/permission-aware redirects per portal |
| RBAC navigation | Hide/show nav items by roles from `/auth/me`; org-context selector for employer/admin (fetch `/organizations`, persist selection) |
| API client polish | Typed endpoint wrappers per domain in `src/lib/api/`; unified error handling (`{"error":{...}}`), toast for 403/429/confirmation-needed |
| UI primitives | Loading skeletons, error states, empty states, confirmation dialog (used by all high-risk actions), notification bell |
| Verification | typecheck/lint/build green; login→dashboard flow works end-to-end against local backend |

**Dependencies:** none. **Blockers:** none (backend is local/scratch-PG ready; no live DB needed).

## WAVE 2 — JOBSEEKER OS

Connect every `jobseeker/*` screen to its canonical endpoint; remove mock/local leftovers; add states.

- Dashboard (`/jobseeker/dashboard`) · Opportunities (`/jobseeker/opportunities`, save/dismiss) · Applications (`/jobseeker/applications`, withdraw; **bulk apply → exact-ID confirmation dialog**) · Offers (`/jobseeker/offers/{id}/decision`) · Interviews (`/jobseeker/interviews`, reschedule request) · Goals/Milestones · Work DNA (questions → assessment → results) · Notifications (unread count + mark read) · Document requests (approve/decline) · Privacy/consents.

**Dependencies:** Wave 1 (auth, guards, org context not needed here but states are). **Verify:** every page's `api.get/post` maps to a real route in `API_CONTRACT.md`.

## WAVE 3 — EMPLOYER / COMPANY OS

- Company profile (`/company/{org}/profile`) · Jobs (create/publish/pause/close) · Pipeline & applications (`/company/{org}/applications{/id}/decision`) · Interviews (create, complete, scorecards, reschedule confirm) · Offers (create/send/withdraw) · Document requests · Dashboard + analytics · Candidates (`/talent/{org}/candidates/search`, saved) · Pools · Skills taxonomy.
- **Org context:** all company routes need `organization_id` — use the Wave 1 org selector.

**Dependencies:** Wave 1 (org context), Wave 2 patterns. **Verify:** cross-tenant UX (an org member never sees another org's data; backend enforces — UI must not cache/shared-store across orgs).

## WAVE 4 — AI (Athena, Career Advisor, Prep, AI Interview)

- **Athena chat UI** (new): `POST /athena/session`, `POST /athena/message`; render tool calls/confirmations; **confirmation dialog for high-risk actions via `POST /athena/confirm` with exact scope + expiry — never auto-confirm**; show `GET /athena/tools`, `GET /athena/usage`.
- **Career Advisor:** `jobseeker/career` — digest, gaps, paths, opportunities, action-plan; render factor explanations; verified vs unverified distinction.
- **Interview Prep:** sessions → questions → answers → evaluation feedback (dimension scores + explanations; never a single "hireability" number).
- **AI Interview:** polish candidate room (`jobseeker/ai-interview`): lobby → device/consent → in-progress (question, progress, controls, `X-Interview-Token`) → feedback; employer side (`employer/ai-interviews`): configure/invite, report (human-review required), **human decision dialog** (advance/reject/hold/follow-up/human-interview).

**Dependencies:** Wave 1. **Verify:** consent cannot be skipped; token flow works; decision is always a human action.

## WAVE 5 — COMMUNICATIONS

- Outreach (employer): create, list, cancel; candidate side accept/decline/report.
- Conversations + messaging (both portals) with read/close/block.
- Notifications bell (shared, from Wave 1) with polling or SSE when available.
- **Contact-info rule:** render only what the API returns as authorized; never raw private contact data.

**Dependencies:** Wave 1.

## WAVE 6 — GOVERNANCE

- Control room: `/governance/dashboard`, reports queue (assign, priority, escalate, team, notes, resolve, reopen), teams/moderators, audit view, integrity signals.
- Enforcement: actions with **creator/approver separation UX**, appeals (file/review/decide/withdraw).
- **Least-privilege UX:** role-aware screens (support ≠ finance ≠ governance).

**Dependencies:** Wave 1 (RBAC nav).

## WAVE 7 — COMMERCE

- Billing self-service: plan, entitlements, usage, invoices, subscription (create/cancel with confirmation), payment **status only**.
- **Never:** client-side refunds, pricing invention, payment credentials, webhook calls from the browser.
- Admin finance (platform role): transactions, invoices, refund workflow, subscriptions — `finance.manage` gated.

**Dependencies:** Wave 1. **Verify:** employer cannot reach `/finance/*` (403) and UI reflects it.

## WAVE 8 — GOVERNMENT

- Integrate **only what exists**: aggregate surfaces behind `workforce.aggregates.read`. No citizen lookup, no individual records, no fabricated intelligence features. Mark architecture/future clearly in the UI (e.g., "foundation only").

## WAVE 9 — FINAL UX / PRODUCTION POLISH

- Loading/empty/error states everywhere · responsive layouts · accessibility (keyboard, ARIA, focus) · navigation & onboarding · permissions UX (explain 403s) · confirmation dialogs for all high-risk actions · security UX (session expiry, MFA, verify-email) · notification patterns · visual consistency · demo readiness against local/scratch backend.
- Final gates: `pytest tests_phase3` (250 passed baseline — must not regress), `npx tsc --noEmit`, `npx eslint src` (0 new warnings), `npm run build`, legacy careers untouched, 63 carried entries untouched.

---

## Cross-wave rules

- **Never invent endpoints** — reuse the 246 documented ones.
- **Never bypass confirmations, RBAC, consent, or document grants.**
- **Never touch** `backend/app`, migrations, legacy `api/`, careers, or the 63 carried entries.
- If a requirement seems to need a backend change: it is out of scope — document it for the owner instead.
- Everything must keep working with `AI_PROVIDER=none`, `PAYMENT_PROVIDER=mock` (safe degraded).