# CURSOR HANDOFF — AskTrabaajo

## A. CURRENT PLATFORM STATUS

```
ASKTRABAAJO BACKEND / PLATFORM:
DEVELOPMENT READY
STAGING READY LOCALLY
CANDIDATE OS (WAVE 2) ACCEPTED
EMPLOYER OS (WAVE 3) IMPLEMENTED
ATHENA UI (WAVE 4) IMPLEMENTED + REFINED
SUPER ADMIN (WAVE 5) IMPLEMENTED
LOCALHOST QA (WAVE 6) IMPLEMENTED

PHASE 19 COMPLETE
WAVE 1 ACCEPTED
WAVE 2 ACCEPTED
WAVE 3 IMPLEMENTED
WAVE 4 IMPLEMENTED
WAVE 5 IMPLEMENTED
WAVE 6 IMPLEMENTED
LIVE RECONCILIATION NOT EXECUTED
NO LIVE DATABASE WRITES PERFORMED
```

- The canonical backend is **complete through Phase 19** plus one Wave 4 status route: 247 `/api/v1` routes, 80 canonical tables, migration head `0014`, RLS, RBAC, Athena, AI Interview, Commerce.
- The live Supabase project (`zrvrjqwboylvvzusorry`) has **not been modified**. Owner confirmed the product is **pre-launch**. Waves 2–5 validated on **isolated sqlite**. See `CURSOR_WAVE_2_DB_CLASSIFICATION.md` and `CURSOR_WAVE_3_DB_CLASSIFICATION.md`.
- Wave 1 is **ACCEPTED**. Wave 2 (Candidate OS) is **ACCEPTED**. Wave 3 (Employer OS) is **IMPLEMENTED**. Wave 4 (Athena UI) is **IMPLEMENTED** and later **refined**. Wave 5 (Super Admin) is **IMPLEMENTED**. Wave 6 (localhost QA + Figma visual validation) is **IMPLEMENTED**. Next: Wave 7 only after a separate approval prompt. Read `CURSOR_DO_NOT_BREAK.md` first.

**Where to start:** `CURSOR_WAVE_6_LOCALHOST_GUIDE.md` + `CURSOR_WAVE_6_CLOSURE.md` + `CURSOR_WAVE_5_CLOSURE.md` + `FRONTEND_GAP_REPORT.md` + `API_CONTRACT.md`. The public flagship site is a **separate** repo (`TheDotProtocol/trabaajowebsite`) — do not merge it into this application.

---

## B. WHAT HAS BEEN BUILT (through Phase 19)

All backend capability is real, tested, and live in `backend/app/`. Do not rebuild it.

| Domain | Status | Where |
|---|---|---|
| Canonical FastAPI modular monolith | ✅ complete | `backend/app/` (main at `backend/app/main.py`) |
| PostgreSQL/Supabase schema + Alembic | ✅ 80 tables, migrations 0001–0014 | `backend/alembic/versions/` |
| UUID identity spine | ✅ all canonical PKs are UUIDs | `backend/app/models/` |
| **Work ID** (person identity) | ✅ | `/api/v1/work-id/*`, models `identity.py`, `work.py` |
| Person/profile architecture | ✅ | `PersonProfile`, `User` in `app/models/identity.py` |
| Organizations / companies / tenancy | ✅ | `/api/v1/organizations`, `/api/v1/company/*`; `tenancy.py` |
| RBAC + permissions | ✅ centralized catalog | `app/models/catalog.py` (roles → permissions) |
| Controlled documents + disclosure | ✅ | `/api/v1/documents/*`, grants, document requests |
| Credentials + verification states | ✅ | `/api/v1/work-id/credentials` (verified/pending/expired/revoked) |
| Jobseeker Employment OS | ✅ | `/api/v1/jobseeker/*` (dashboard, goals, milestones, work-dna, offers, interviews, notifications) |
| Employer/Company Employment OS | ✅ | `/api/v1/company/*` (profile, jobs, pipeline, interviews, offers, analytics) |
| Opportunities + matching | ✅ | `/api/v1/jobseeker/opportunities`, `talent.py` models |
| Applications + pipeline | ✅ | `/api/v1/jobseeker/applications`, `/company/*/applications` |
| Offers | ✅ | `/api/v1/jobseeker/offers`, `/company/*/offers` |
| Talent Graph + skills taxonomy | ✅ | `/api/v1/talent/*` (skills, pools, candidates, discovery) |
| Outreach + conversations + messaging | ✅ | `/api/v1/talent/*/outreach`, `/communications`, `/jobseeker/outreach` |
| Notifications + events | ✅ | `/api/v1/jobseeker/notifications`, `/api/v1/events` |
| Governance / enforcement / appeals / audit | ✅ | `/api/v1/governance/*`, `/api/v1/enforcement/*` |
| **Athena AI Core** | ✅ 39 controlled tools | `/api/v1/athena/*` |
| Career Advisor | ✅ deterministic + AI explanation | `/api/v1/career-advisor/*`, `/jobseeker/advisor` |
| Interview Preparation | ✅ structured mock interview | `/api/v1/interview-prep/*` |
| **AI Interview Engine** | ✅ full orchestration | `/api/v1/ai-interviews/*` |
| Commerce / billing / payments / finance | ✅ mock provider | `/api/v1/billing/*`, `/api/v1/finance/*` |
| Government intelligence | ✅ architecture + aggregate-only surfaces | `workforce.aggregates.read` permission; no citizen lookup |
| Security / RLS | ✅ | RLS policies in migrations 0010+; session context `app/db/session.py` |
| Legacy Careers boundary | ✅ preserved untouched | `api/`, `frontend/src/app/careers/*`, `frontend/src/lib/careers/*` |

**Verification:** `PHASE_19_REPORT.md` (latest), `PHASE_18_REPORT.md`, `PHASE_16_REPORT.md` (AI interview), `PHASE_17_REPORT.md` (commerce). Each phase's companion docs detail the architecture.

---

## C. CANONICAL VS LEGACY (know the difference)

| Layer | CANONICAL (build on this) | LEGACY (preserve, do NOT build on) | REFERENCE-ONLY |
|---|---|---|---|
| Backend | `backend/app/` — FastAPI modular monolith, `/api/v1`, 246 routes | `backend/main.py` + root `api/` — 107 routes, careers-era prototype (facial-analysis interviews, Supabase REST, simple_database) | `backend/simple_main.py`, `debug_db.py`, old tests |
| Database | Alembic migrations 0001–0014 → 80 canonical tables, UUID PKs, RLS, app role `asktrabaajo_app` | Live Supabase `public` schema: 21 legacy tables (`companies`, `jobs`, `profiles`, `payments`, `interviews`…) | `supabase-careers-schema.sql`, `supabase-schema.sql` (historical SQL dumps) |
| Frontend | `frontend/src/lib/api/{client,session,types}.ts` + pages under `jobseeker/`, `company/`, `admin/`, `employer/`, `id/` | `frontend/src/lib/careers/*` (careers site), `src/lib/supabase.ts`, `src/lib/localAuth.ts`, `src/hooks/useAuth.ts`, `dashboard/`, `interviews/`, `interview/` | `mock.js`, `testUser.ts` |

**Rules:**
- New UI work consumes the **canonical API** (`/api/v1`) through `frontend/src/lib/api/`.
- The **legacy Careers site stays as-is** (public marketing/jobs pages reading legacy Supabase). Do not migrate it into the canonical domain during UI integration.
- The old Supabase schema is **historical product data** — preserved, never the target for new features.
- The 63 carried Phase-1 working-tree entries (legacy edits from early phases) are **untouched, uncommitted, and must stay that way**.

---

## D. BACKEND ROUTE INVENTORY (from the actual code — 246 routes)

Generated by importing `backend/app/main.py` (see `API_CONTRACT.md` for the full per-route listing). Groups by prefix:

| Prefix | Count | Purpose | Auth | Key permissions |
|---|---|---|---|---|
| `/api/v1/auth` | 16 | register, login, refresh, logout, me, MFA, email verify, password | none (register/login) / token | self only |
| `/api/v1/work-id` | 26 | profile, skills, experiences, employments, educations, credentials, consents, privacy, completion | token | self (owner) |
| `/api/v1/documents` | 7 | upload, view, grants (controlled disclosure) | token | owner; grants authorize employers |
| `/api/v1/jobseeker` | 46 | dashboard, opportunities, applications, interviews, offers, goals, milestones, work-dna, notifications, communications, outreach, document-requests | token | self |
| `/api/v1/career-advisor` | 6 | digest, gaps, paths, opportunities, applications, action-plan | token | self |
| `/api/v1/interview-prep` | 7 | sessions, questions, answers, complete | token | self |
| `/api/v1/ai-interviews` | 19 | employer: create/invite/decision/report; candidate: claim/consent/start/respond/complete | token + entry token (candidate side) | `interviews.manage` (employer) |
| `/api/v1/athena` | 9 | status, sessions, message, confirmations, tools, usage, modes | token | self + high-risk confirmations |
| `/api/v1/organizations` | 7 | org CRUD, members | token | owner/admin; platform/government kinds need super admin |
| `/api/v1/company` | 25 | profile, jobs, pipeline, applications, interviews, offers, analytics, document-requests | token | org-scoped: `jobs.*`, `applications.*`, `interviews.*`, `offers.*` |
| `/api/v1/talent` | 27 | skills taxonomy, pools, candidates search/discovery, outreach, communications | token | org-scoped: `candidates.search`, `pools.manage`, `talent.outreach.*` |
| `/api/v1/governance` | 21 | reports, teams, moderators, dashboard, signals, audit | token | platform moderator/admin (`governance.*`) |
| `/api/v1/enforcement` | 15 | actions, appeals, state | token | creator/approver separation, appeals |
| `/api/v1/billing` | 9 | plans, subscription, entitlements, invoices, usage, webhooks | token | `billing.read`/`billing.manage` (org); webhook = HMAC signature |
| `/api/v1/finance` | 5 | transactions, invoices, refunds, subscriptions | token | `finance.read`/`finance.manage` (platform only) |
| `/api/v1/events` | 2 | notifications feed, mark read | token | self |

**Every canonical route:** validates the bearer token; resolves the actor's user + person; enforces RBAC via `require_org_permission` / `require_super_admin` / self-scope; scopes queries to the actor's org/person; writes audit rows for meaningful actions. Errors use the envelope `{"error":{"code","message","details"}}`.

**There are NO government citizen-lookup routes, NO facial-analysis routes, NO lie-detection routes, NO autonomous hiring routes.** Do not add any.

---

## E. FRONTEND INTEGRATION MAP (honest status)

Canonical client layer **already exists**: `frontend/src/lib/api/client.ts` (`ApiClient`), `session.ts` (token storage `asktrabaajo_at`/`asktrabaajo_rt`, `api` singleton, `fetchMe`, `login`, `logout`), `types.ts` (response types). ~28 pages already import `lib/api` and call real canonical endpoints.

| Surface | Pages | Status |
|---|---|---|
| Auth (login/register) | `login/page.tsx`, `register/page.tsx` | **WAVE 1 COMPLETE** — public pages write `asktrabaajo_at` / `asktrabaajo_rt` via `POST /api/v1/auth/*`. Refresh, `PortalGuard`, `OrgProvider`, `OsChrome` are in place. |
| Jobseeker portal | `jobseeker/*` | **WAVE 2 COMPLETE** — CandidateShell + API-backed Employment OS |
| Employer/company | `company/*`, `employer/ai-interviews`, `employer/billing` | **WAVE 3 COMPLETE** — EmployerShell + Employment OS. **WAVE 4** Athena HR workspace is live (degraded-honest when the provider is unset). |
| Admin/governance | `admin/*` (command center, governance, enforcement, appeals, audit, teams, finance, support, operations) | **WAVE 5 COMPLETE** — Super Admin Figma shell + canonical APIs. Least privilege. No user-directory fabrication. |
| Work ID | `id/work-id`, `id` | **WAVE 2 COMPLETE** — Candidate-styled Work ID + account/security |
| Legacy dashboard/interviews | `dashboard/*`, `interviews/*`, `interview/*` | **LEGACY** — use `useAuth`/Supabase; leave as-is or migrate in later waves (not careers) |
| Careers site | `careers/*` | **LEGACY — DO NOT TOUCH** (separate data source) |
| Mock/local pages | `interview/[id]/analysis` | **LEGACY / MOCK** — mark clearly; never present as production |

**Biggest remaining gaps (detail in `FRONTEND_GAP_REPORT.md`):** Athena session history API; live AI provider; first-class offices/departments/job-template catalogs; Figma workforce/performance/learning/onboarding; Figma People/Companies/Governments directories (no APIs); government portal absent; public website CTAs still placeholder. Waves 1–5 are implemented.

---

## F. CANONICAL PORTAL ARCHITECTURE (intended structure)

**JOBSEEKER PORTAL** (`/jobseeker/*`): dashboard · Work ID (`/id/work-id`) · professional profile · credentials · documents (`/documents`) · verification · Work DNA assessment · career goals & milestones · opportunities · applications · application tracking · interviews · AI Interview (`/jobseeker/ai-interview`) · Interview Preparation (`/jobseeker/interview-prep`) · Career Advisor (`/jobseeker/career`, `/career-advisor/*`) · offers · communications & outreach · notifications · privacy/consent (`/work-id/consents`, `/work-id/privacy`) · settings.

**EMPLOYER / COMPANY PORTAL** (`/company/*`, `/employer/*`): dashboard · company profile (`/company/{org}/profile`) · organization & members (`/organizations/{org}/members`) · jobs (create/publish/pause/close) · candidate pipeline · candidate discovery & Talent Graph (`/talent/*`) · applications · interviews · AI Interviews (`/employer/ai-interviews`) · candidate reports · offers · communications · **billing** (`/employer/billing`: plan, usage, entitlements, invoices; `billing.read` boundary) · analytics · settings.

**GOVERNANCE / SUPER ADMIN** (`/admin/*`): command center · governance cases (`/governance/reports`) · teams & moderators · priority/SLA/escalation · audit (`/governance/audit`) · enforcement actions + approval separation (`/enforcement/actions`) · appeals (`/enforcement/appeals`) · platform finance (`/finance/*`; `finance.read`/`finance.manage` only) · support/operations honesty pages. Super Admin is **not** unrestricted private-data access. See `CURSOR_ADMIN_DESIGN_DECISIONS.md`.

**GOVERNMENT:** **architecture/foundation only** — `government_admin`/`government_user` roles with `workforce.aggregates.read`; aggregate-only surfaces. **No citizen lookup, no individual records, no government intelligence product exists.** Do not fabricate government UI beyond what exists.

---

## G. AUTHENTICATION (canonical — do not duplicate)

- **Register/Login:** `POST /api/v1/auth/register`, `/login` → `TokenPair {access_token, refresh_token}`; optional MFA (`/mfa/*`); email verify (`/verify-email/*`); password lifecycle (`/forgot-password`, `/reset-password`, `/change-password`).
- **Tokens:** short-lived JWT access (15 min) + rotating refresh (30 days). `POST /auth/refresh` rotates; `POST /auth/logout` + `POST /auth/sessions/revoke-all` revoke. `GET /auth/me` returns user + roles.
- **Session identity:** server-side only — `app/db/session.py` sets `app.current_user_id` / `app.current_org_ids` from the authenticated actor per request, reset at checkout; RLS policies (`current_setting`) are inert without it. Never client-controlled.
- **RBAC:** `app/models/catalog.py` — roles (`org_admin`, `hr`, `recruiter`, `hiring_manager`, `customer_support`, `finance`, `government_*`, platform admins) → permissions; `require_org_permission`, `require_super_admin` in `app/api/deps` (permission checks).
- **Frontend rule:** use `frontend/src/lib/api/session.ts` (`setSession`/`getAccessToken`/`login`/`logout`/`fetchMe`). **DO NOT create a second auth system.** Wave 1 wired rotating refresh (`POST /auth/refresh`, single-flight) on the existing `ApiClient`. Access tokens remain in localStorage (`asktrabaajo_at` / `asktrabaajo_rt`) — accepted for now; do not change backend token storage unless a later approved phase requires it.

---

## H. WORK ID (identity spine)

- **Ownership:** one `PersonProfile` per user; every Work ID record is user-owned and user-scoped.
- **Contents:** professional profile, experiences, employments, educations, skills, credentials (with verification state: verified/unverified/pending/expired/revoked/user-provided/system-derived), career goals/milestones.
- **Visibility & consent:** `/work-id/privacy` (visibility settings), `/work-id/consents` (candidate-controlled), `/documents` grants + document requests (`/jobseeker/document-requests`, `/company/{org}/document-requests`) with candidate approve/decline. **OTP-controlled disclosure** exists where implemented in the document-request flow — preserve it.
- **Employer access:** only via explicit grants/requests — never blanket. The Talent Graph only surfaces what the candidate allows.
- **Cursor rule:** Work ID screens must render verification state truthfully (never show unverified as verified) and must not bypass consent/grants.

---

## I. ATHENA (AI core — 8 routes, 39 tools)

- **Architecture:** provider abstraction (`app/services/ai_provider.py` style; `AI_PROVIDER` = `none` (safe default/degraded) | `openai`). No provider credential → clear `AI_PROVIDER_UNAVAILABLE` error, never fabricated responses.
- **Routes:** `POST /athena/session`, `POST /athena/message`, `POST /athena/confirm`, `GET /athena/confirmations`, `POST /athena/session/{id}/close`, `GET /athena/tools`, `GET /athena/usage`, `GET /athena/modes`.
- **Tool registry:** 39 controlled tools (inspection + read-only + scoped mutations). Every tool declares allowed modes, permissions, data scope, risk, confirmation requirement, audit. **No SQL, filesystem, shell, arbitrary HTTP, or code-execution tools.**
- **High-risk actions:** require explicit, **exact-scope** confirmation with expiration (`POST /athena/confirm`); reauthorization on each execution; bulk scopes (e.g. bulk applications) bind to exact IDs — if the set changes, confirmation is void.
- **Data minimization:** Athena receives structured digests, never raw DB dumps; excluded: government IDs, KYC, credentials/passwords, private doc contents, unnecessary contact data.
- **Rate limits/budgets:** per-user daily budgets (`athena_daily_messages_per_user`, `athena_daily_tool_calls_per_user`), TTL sessions/confirmations, usage logged (`GET /athena/usage`).
- **Frontend rule:** show tool calls/confirmations truthfully; **never auto-confirm**; surface budget/rate-limit errors as user messages.

---

## J. CAREER ADVISOR (deterministic core + AI explanation)

- **Deterministic (from canonical data, no LLM):** `GET /career-advisor/digest` (Career Profile Digest from Work ID), `/gaps` (skill-gap analysis against canonical skills taxonomy + job requirements + career paths), `/paths` (DIRECT/ADJACENT/TRANSITION/EXPLORATORY using Talent Graph career paths), `/opportunities` (matching via the existing matching engine: strong/potential/career_transition/explore), `/applications` (application-history analysis within authorized scope), `/action-plan` (structured suggestions; never guarantees).
- **AI role:** explains the deterministic results (`/jobseeker/advisor` chat). Athena never invents skills, salaries, market data, or outcomes.
- **Frontend rule:** render recommendations with their factor explanations; distinguish verified vs unverified; no fabricated outcomes; recommendations are suggestions unless the user acts.

---

## K. AI INTERVIEW (full engine — 19 routes)

**Employer side:** `POST /ai-interviews` (configure type, duration, competencies, difficulty, count, language, intro/closing, consent_required, media flags) → `POST /{id}/invite` → `GET /{id}/report` → `POST /{id}/decision` (advance/reject/hold/follow-up/human-interview). Employer actions require `interviews.manage` in the org.

**Candidate side (entry-token bound):** `POST /claim` (token returned **once**, SHA-256 stored) → `POST /{id}/consent` (per-capability mic/camera/recording) → `POST /{id}/start` → `GET /{id}/next-question` → `POST /{id}/responses` → `POST /{id}/repeat` (never penalized) → `POST /{id}/pause|resume` → `POST /{id}/complete` → `GET /{id}/feedback` (candidate) → `POST /{id}/integrity-signals` (session-level signals only, labeled REVIEW SIGNALS).

**Security model:** wrong token/wrong person/replay → 403, no existence oracle; consent before start; explicit state machine (scheduled→waiting→consent_required→ready→in_progress→completed…); questions validated against competencies + **prohibited-topic gate** (no protected characteristics, no facial/lie/emotion framing); **raw answers never persisted**; evaluations are explainable 1–5 dimension scores with explanations, no single "hireability" number; reports carry "AI-assisted assessment. Human review required."

**Hard restrictions (tested):** NO facial emotion inference · NO lie detection · NO protected-characteristic inference · NO autonomous hiring · NO raw answer storage.

---

## L. COMMUNICATIONS

- Outreach (employer → candidate): `/talent/{org}/outreach/*` + `/jobseeker/outreach/{id}` (accept/decline/report) with cooldown/expiry abuse controls.
- Conversations: `/talent/{org}/communications/*` and `/jobseeker/communications/*` (create, messages, read state, close, blocks).
- Contact-information protection: the API returns what the candidate authorized; **never render raw private contact info** the candidate hasn't exposed.
- Notifications: `/jobseeker/notifications*`, `/events*`.

---

## M. GOVERNANCE / ENFORCEMENT / APPEALS

- Governance: `/governance/reports` (report, assign, priority, escalate, team, notes, links, resolve, reopen), `/governance/teams`, `/governance/moderators`, `/governance/dashboard`, `/governance/signals`, `/governance/audit`. Platform moderator/admin permissions.
- Enforcement: `/enforcement/actions` with **creator/approver separation** (create → approve/reject/revoke), `/enforcement/appeals` (file, assign, review, decide, withdraw), `/enforcement/state/me`.
- Least privilege is enforced server-side; the UI must reflect it (a support user must not see finance actions, etc.).

---

## N. COMMERCE

- Plans/entitlements: `/billing/plans`, `/billing/entitlements`; FREE plan seeded (price 0.00 — **no pricing invented**).
- Subscription: `/billing/subscription`, `POST /billing/subscriptions`, `/billing/subscriptions/cancel` (org-owned, explicit state machine).
- Invoices/usage: `/billing/invoices{/id}`, `/billing/usage`.
- Webhooks: `POST /billing/webhooks/{provider}` — HMAC-signed, replay/duplicate/idempotency protected; never client-callable as arbitrary payment events.
- Finance (platform only): `/finance/transactions`, `/finance/invoices`, `/finance/refunds` (GET+POST), `/finance/subscriptions` — `finance.manage`; org users and support **cannot** refund.
- Money: NUMERIC/Decimal, explicit currencies (USD default), provider references only (never card data), mock/sandbox provider (`PAYMENT_PROVIDER=mock`). **No production payment activation.**
- Frontend: `billing` UI is read-only self-service; **no client-side authority for refunds or financial actions**.

---

## O. LIVE DATABASE STATUS (no credentials here)

- Project: `zrvrjqwboylvvzusorry` (Supabase) · PostgreSQL **17.6** · db `postgres` · schema `public` · TZ UTC · **session pooler** connection in `backend/.env` (gitignored).
- Live: **21 legacy tables**, RLS enabled on all, `alembic_version` **absent**, `asktrabaajo_app` **absent**.
- Collision: exactly one — legacy `interviews` (0 rows, 0 incoming FKs, retired prototype) vs canonical `interviews` (migration 0003). Validated safe rename: `interviews → legacy_asktrabaajo_interviews` (`scripts/db/reconcile_legacy_interviews.sql`).
- Expected after reconciliation: **101 tables** (21 legacy + 80 canonical), `alembic_version=0014`, `asktrabaajo_app` with 316 grants (79 tables × 4), zero legacy grants, not superuser.
- **NO LIVE RECONCILIATION HAS BEEN EXECUTED.** Gate: operator confirms **Backup/PITR** in the Supabase dashboard. Do not run it from the frontend work.

---

## P. TEST / VALIDATION STATUS (latest actual results)

| Check | Result |
|---|---|
| SQLite full suite (`backend`: `pytest tests_phase3`) | **251 passed / 11 skipped** without PG; **262 passed** with local `p14_test` (Wave 4) |
| Wave 2 Candidate E2E (`scripts/wave2_candidate_e2e.py`) | **PASS** (isolated sqlite; hosted DB untouched) |
| Wave 3 Employer E2E (`scripts/wave3_employer_e2e.py`) | **PASS** (isolated sqlite; hosted DB untouched; cross-tenant 403/404) |
| Wave 4 Athena E2E (`scripts/wave4_athena_e2e.py`) | **PASS** (degraded provider honest; mode/tenant isolation) |
| Wave 5 Super Admin E2E (`scripts/wave5_admin_e2e.py`) | **PASS** (governance → enforcement separation → appeal → audit → finance/RBAC 403s) |
| PostgreSQL RLS suite (scratch PG 16 @ 0014) | **11/11 passed** |
| Staging-mode E2E smoke (PG 16, `ENVIRONMENT=staging`) | **PASS** (`P19_STAGING_SMOKE_PASS`: auth → org → AI interview full journey → report → human decision → billing boundary → cross-tenant denial) |
| Frontend typecheck (`tsc --noEmit`) | PASS |
| Frontend lint (`eslint src`) | PASS — 0 errors, 5 pre-existing warnings |
| Frontend build (`next build`) | PASS |
| Canonical routes | 246 (import-verified) |
| Legacy routes | 107 (import-verified, unchanged) |
| Migration roundtrip | Clean on SQLite + PG (incl. 0013/0014) |
| Secret scan | CLEAN (only config-name references + empty `.example` templates) |

**How to run:** `cd backend && .venv/bin/python -m pytest tests_phase3` · RLS: `TEST_PG_URL=postgresql://asktrabaajo_app@127.0.0.1:5432/p14_test TEST_PG_OWNER_URL=postgresql://mac@127.0.0.1:5432/p14_test ... pytest tests_phase3/test_rls_phase13.py` · Frontend: `npx tsc --noEmit && npx eslint src && npm run build`.

---

## Q. KNOWN BLOCKERS (only real ones)

1. **Backup/PITR not confirmed** (Supabase dashboard) — blocks live reconciliation.
2. **Live reconciliation not authorized** — validated plan ready, execution needs operator go-ahead.
3. **Remote staging infrastructure not provisioned** — separate Supabase project recommended (not auto-created).
4. **Distributed rate limiting** — in-process `memory` store default; `RATE_LIMIT_STORE=db` or Redis required for multi-instance production.
5. **Providers not provisioned:** AI (`none` default), payments (`mock`), email (none), voice/video STT/TTS (`none`).
6. **Legacy anon/service keys stale** — operator rotates when legacy REST is re-enabled.

---

*Authoritative companion docs: `API_CONTRACT.md` (routes), `FRONTEND_GAP_REPORT.md` (gaps), `CURSOR_UI_INTEGRATION_PLAN.md` (waves), `CURSOR_DO_NOT_BREAK.md` (rules), `PHASE_19_REPORT.md` + phase docs 12–19 (architecture/security).*