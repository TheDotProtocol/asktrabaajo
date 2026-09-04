# CURSOR INTEGRATION START REPORT

**Date:** 2026-09-05  
**Git HEAD:** `d51d78f` on `main` at reconnaissance; Wave 1 implemented afterward.  
**Scope:** reconnaissance originally. **Wave 1 is now implemented** — see `CURSOR_WAVE_1_REPORT.md`.

**Wave 1 status:** public `/login` and `/register` establish the canonical session. Refresh, guards, org context, and the functional OS shell are in place. Do not start Wave 2 until reviewed.

```
WHAT WE HAVE          canonical backend complete through Phase 19
                      + functional-proof frontend pages that already call /api/v1
                      + Wave 1 canonical login/register/session/guards/org/shell
                      + polished marketing/careers UI that is LEGACY
                      + four Figma portal files that are DESIGN, not code

WHAT IS CONNECTED     /login /register → canonical /api/v1/auth
                      ~29 canonical pages → typed ApiClient → /api/v1
                      with a real session after public login

WHAT IS NOT CONNECTED Athena UI, /career-advisor/* screens,
                      Figma portal shells, government portal, most Super Admin Figma,
                      page-level empty/loading polish, MFA enroll UX

WHAT TO FIX NEXT      Wave 2 — Jobseeker OS (real-data polish, remaining Work ID,
                      notifications, document requests) — after Wave 1 review

WHAT MUST NEVER BE    canonical backend, migrations, live DB, careers, remaining
TOUCHED               Phase-1 carried files, secrets, invented endpoints
```

---

## 1. Current frontend architecture

Next.js 15 App Router (`frontend/`), React 19, Tailwind 4, lucide-react. **No** React Query, **no** Zustand, **no** form library, **no** design-system package. Canonical data access is a hand-written fetch client.

There are **four distinct frontends sharing one Next app**:

| Layer | Where | Visual | Data | Status |
|---|---|---|---|---|
| Marketing site | `/`, `/about`, `/features`, `/leadership`, `/contact` | Gold brand (`#D4AF37`), Geist, dark mode | none | Public site. |
| Auth entry | `/login`, `/register`, `/forgot-password` | Gold brand (preserved) | Canonical `/api/v1/auth` | Wave 1 connected. |
| Legacy Careers | `/careers/*`, `src/lib/careers/*` | Polished careers site | Legacy Supabase REST | **DO NOT TOUCH** |
| Legacy product dashboards | `/dashboard/*`, `/interviews/*`, `/interview/*` | Older gold UI; some careers panels | `useAuth` + Supabase + careers APIs | **LEGACY.** Includes facial-analysis interview UI. Leave it. |
| Canonical functional-proof OS | `/jobseeker/*`, `/company/*`, `/employer/*`, `/admin/governance/*`, `/id/*` | Neutral Tailwind “proof shells” — **not Figma** | `src/lib/api/session.ts` → `/api/v1` | **Wave 1:** real login session + `PortalGuard` + `OsChrome` + `OrgProvider`. Pages still thin (not Figma). |

**There is no Figma-derived React implementation in this repo.** Layout comments on the canonical shells say this explicitly: *“NOT the final product UI — the Figma design system replaces this shell later.”*

**Wave 1 chrome:** `ConditionalChrome` is standalone for `/careers`, `/dashboard/candidate|employer`, `/jobseeker`, `/company`, `/employer`, `/admin`, `/id`, `/forbidden`. `Providers` is Theme → Auth → Org. No toast system yet.

**Environment:** `frontend/.env.example` documents `NEXT_PUBLIC_API_URL=http://localhost:8000` plus leftover Legacy Careers Supabase keys (unused by canonical auth). The client defaults to `http://localhost:8000` when unset. No secrets belong in `NEXT_PUBLIC_*`.

---

## 2. Current authentication architecture

**Wave 1 closed the dual-auth gap for the canonical application.** Legacy `useAuth` remains only for Careers / `/dashboard` / `/interview*`.

### Canonical (the one we must use)

| Piece | Location | Behavior |
|---|---|---|
| Backend | `backend/app/api/v1/auth.py` | 16 routes: register, login, refresh, logout, me, MFA, email verify, password, sessions |
| Register body | `RegisterRequest` | `email`, `password` (≥8), `full_name` only. **No role field.** Person is created with the user. Org roles come later via memberships. |
| Tokens | JWT | Access 15 min + rotating refresh 30 days. `POST /auth/refresh` rotates. |
| Frontend session | `frontend/src/lib/api/session.ts` | `asktrabaajo_at` / `asktrabaajo_rt` in localStorage. `login`, `registerAccount`, `completeMfa`, `logout`, `fetchMe`, `refreshSession`. |
| Client | `frontend/src/lib/api/client.ts` | Bearer header. On 401: single-flight refresh + retry; auth endpoints never retry. |
| Working UI | `/login`, `/register`, `/forgot-password`, `/id` | Public login/register write the canonical session. `/id` is account settings, not a second login. |

`GET /auth/me` returns `user_id`, email, person, **memberships** (org + role), **permissions**, `super_admin`. That is the RBAC source for navigation. Backend remains authoritative.

### Legacy (do not extend)

| Piece | Location | Behavior |
|---|---|---|
| Hook | `src/hooks/useAuth.ts` | Supabase `signInWithPassword` / `signUp` + `localAuth.ts` privileged local-session fallback + `testUser.ts` |
| Public pages | `/login`, `/register` | Call `useAuth`. Success → `router.push('/dashboard')` (legacy dashboard). **Never writes `asktrabaajo_at`.** |
| Prefill | login/register | Prefills `TEST_USER` from `NEXT_PUBLIC_TEST_USER_*`. |

**Consequence:** a user who “logs in” at `/login` has a legacy session and **empty canonical storage**. Every `/jobseeker`, `/company`, `/admin` page then either redirects to `/id` (if it checks `getAccessToken`) or fires 401s. That is why the product does not feel connected.

**Register role picker is not canonical.** The public register page offers jobseeker / employer / HR / government / foreign company. Canonical register does not accept a role. Wave 1 must not invent a role payload. After register: person exists; employer path creates an org via `POST /organizations`; government/platform kinds require super admin.

**Forgot-password** is linked from `/login` (`/forgot-password`) but **no page exists**. Backend routes exist.

---

## 3. Canonical API integration status

Backend: `backend/app/` FastAPI modular monolith, **246** `/api/v1` routes, 80 tables, Alembic head `0014`. Verified in repo (`backend/app/api/v1/router.py` matches `API_CONTRACT.md`).

Frontend canonical client is used by **29 page files**. Types in `src/lib/api/types.ts` are ahead of the UI (Career Advisor, Athena, commerce types exist; many screens do not).

| Domain | Backend | Frontend wiring | Honest status |
|---|---|---|---|
| Auth | 16 routes | `/id` only; public login/register legacy | **GAP** |
| Work ID | 26 routes | `/id/work-id` profile/skills/experience/education/employment/credentials/documents | **PARTIAL** — no privacy/consents UI |
| Documents | 7 routes | upload/list/delete on Work ID page | **PARTIAL** — grants UI thin/absent |
| Jobseeker OS | 46 routes | dashboard, opportunities, applications, interviews, offers, work-dna, communications, goals | **PARTIAL** — real GETs/POSTs; no bulk-apply confirmation; no notifications page; no document-request inbox |
| Career Advisor | 6 routes `/career-advisor/*` | **zero calls** in `frontend/src` | **API EXISTS / UI MISSING** (page uses `/jobseeker/advisor` + `/jobseeker/career/intelligence` instead) |
| Interview Prep | 7 routes | `/jobseeker/interview-prep` | **PARTIAL** — wired |
| AI Interviews | 19 routes | candidate `/jobseeker/ai-interview`; employer `/employer/ai-interviews` | **PARTIAL** — claim/consent/start/respond/complete + report + human decision exist |
| Athena | 8 routes, 39 tools | **zero calls** | **API EXISTS / UI MISSING** |
| Organizations | 7 routes | list/create on company home; members UI missing as a product screen | **PARTIAL** |
| Company OS | 25 routes | dashboard, jobs (create/publish/pause/close), pipeline, document-requests, offers | **PARTIAL** — org id duplicated per page via `localStorage asktrabaajo_org_id` |
| Talent Graph | 27 routes | search, saved, pools, outreach, candidate profile | **PARTIAL** |
| Communications | jobseeker + talent | both inboxes, messages, read, close, outreach accept/decline | **PARTIAL** — no shared bell; blocking UI uncertain |
| Notifications / events | jobseeker notifications + `/events` | events feed inside communications pages only | **PARTIAL** |
| Governance | 21 routes | control room, case detail, teams, audit, signals | **PARTIAL** — proof UI |
| Enforcement / appeals | 15 routes | list + detail, approve/reject/revoke, decide | **PARTIAL** |
| Billing | 9 routes | `/employer/billing` plans/subscription/entitlements/invoices | **PARTIAL** — read-only self-service, mock provider. Correct: no client payment authority |
| Finance | 5 routes | **no page** | **API EXISTS / UI MISSING** (platform `finance.manage` only) |
| Government | aggregate permission only | **no page** | **FOUNDATION** — Figma is not a live product |

No raw `fetch()` in app pages. Canonical pages do not import Supabase.

---

## 4. Legacy integration points

Leave these as-is. Do not migrate them into the canonical domain during UI integration.

| Surface | Path / files | Why it exists |
|---|---|---|
| Careers public site | `frontend/src/app/careers/*`, `src/lib/careers/*`, `src/components/careers/*` | Separate marketing/jobs product on legacy Supabase |
| Legacy auth | `useAuth.ts`, `localAuth.ts`, `testUser.ts`, `lib/supabase.ts`, `lib/supabaseStorage.ts` | Careers + old dashboards |
| Legacy dashboards | `/dashboard`, `/dashboard/candidate`, `/dashboard/employer` | Pre-canonical product UI |
| Legacy interviews | `/interviews`, `/interview/[id]`, `/interview/[id]/analysis`, `InterviewRoom.tsx` | Prototype including **facial analysis** — forbidden in canonical platform |
| Legacy backend | `backend/main.py` + `api/` (~107 routes) | Careers-era FastAPI |
| Live Supabase schema | 21 legacy tables, no `alembic_version` | Historical data. **Reconciliation not executed. Do not run it.** |
| Carried Phase-1 tree | **63** unstaged files (see §10) | Frozen leftovers. Do not commit, “clean up,” or silently edit. |

`localAuth.ts` is a privileged local-session fallback — the most dangerous legacy auth artifact. Wave 1 must not call it from canonical surfaces.

---

## 5. Exact Wave-1 changes required

Do Wave 1 before any portal polish. Backend is already ready. No live DB needed (local/scratch SQLite or PG).

1. **API base URL**  
   Add `frontend/.env.example` with `NEXT_PUBLIC_API_URL` only (e.g. `http://localhost:8000`). Do not put secrets in the frontend.

2. **One session**  
   Public `/login` and `/register` must call canonical `session.ts` (`login` / `POST /auth/register` + `setSession`). Redirect by memberships: person-only → `/jobseeker`; employer org → `/company`; platform governance → `/admin/governance`. Never `/dashboard`.  
   **Process conflict:** those two pages are in the 63 carried files. Wave 1 cannot succeed without an owner exception to replace them (recommended: exception for `login/page.tsx` + `register/page.tsx` only). `/id` already proves the contract.

3. **Register mapping**  
   Send `{ email, password, full_name }`. Drop the fake role catalog from the canonical submit path. Employer org creation is a later step (`POST /organizations`), not a register field.

4. **Refresh**  
   Wire `POST /auth/refresh` with rotation. On 401: refresh once, retry the original request, then clear + redirect to login. Stop using “401 → wipe tokens” as the only behavior. Access token should move toward memory; refresh token stays httpOnly-or-localStorage until a later hardening pass. Do not create a second token scheme.

5. **Logout**  
   `POST /auth/logout` + `clearSession()` from a shared portal nav (not only `/id`).

6. **Route guards**  
   Shared client guard: no access token → `/login`. Optional `fetchMe` gate. Portal guards: jobseeker (authenticated person), company (employer/recruiter membership), admin (governance permissions / super admin). Never treat a frontend role check as authorization.

7. **Org context**  
   One `OrgProvider` reading `GET /organizations` / `me.memberships`, persisting `asktrabaajo_org_id`, passing `organization_id` into company/talent/billing calls. Delete the copy-pasted `ORG_KEY` blocks on each company page after the provider exists.

8. **Chrome isolation**  
   Canonical portals must not sit inside the marketing Header/Footer. Figma shells (sidebar + command surface) replace the proof header. **`layout.tsx`, `ConditionalChrome.tsx`, `Providers.tsx` are also in the 63.** Need owner exception to exclude `/jobseeker`, `/company`, `/employer`, `/admin`, `/id` from marketing chrome — or add a new layout path that does not edit those files.

9. **Error / loading / empty primitives**  
   Reusable states + a confirmation dialog (Athena confirm, bulk apply, enforcement). Toast for 403 / 429 / confirmation-needed. Do not add a new component library.

10. **Do not build MFA/verify-email as Wave 1 product** — backend exists; `/id` already exercises them. A polished MFA step on login is Wave 9 unless login already hits `mfa_required`.

**Verification:** `npx tsc --noEmit`, `npx eslint src`, `npm run build`, then login → `/jobseeker` against local canonical backend. Do not run live reconciliation. Do not start `pytest` against production.

---

## 6. Portal-by-portal integration status

### Jobseeker OS — PARTIAL (proof UI + many real calls)

Figma file: [asktrabaajo — Candidate](https://www.figma.com/design/AvJb5GfMmbhR0vgQW9pLUO/asktrabaajo---Candidate) (`AvJb5GfMmbhR0vgQW9pLUO`)

| Figma screen | Code today | Backend | Integrate? |
|---|---|---|---|
| sign-in / sign-up | `/login` `/register` legacy; `/id` canonical | `/auth/*` | Wave 1 |
| home (Command Surface) | `/jobseeker` → `GET /jobseeker/dashboard` | live | Wave 2 + Figma shell |
| Work ID | `/id/work-id` | `/work-id/*`, `/documents` | Wave 2 |
| Athena | **missing** | `/athena/*` | Wave 4 |
| Work DNA | `/jobseeker/work-dna` | live | Wave 2 |
| Career / career-map / career-development | `/jobseeker/career` uses advisor + goals + intelligence | `/career-advisor/*` unused | Wave 5 |
| Opportunities / applications / interviews / offers | matching pages, real API | live | Wave 2 |
| Credentials | inside Work ID | live | Wave 2 |
| Messages | `/jobseeker/communications` | live | Wave 5/7 |
| Notifications / Settings | nav in Figma; no pages | notifications + privacy/consents APIs | Wave 2/7 |
| skills-intelligence / compensation / onboarding | no pages | not first-class APIs | **COMING / not yet available** — do not fake |

### Employer / Company OS — PARTIAL

Figma file: [AskTrabaajo — HR](https://www.figma.com/design/TWxgrQJPdyGSsbTkM8gX1b/AskTrabaajo---HR) (`TWxgrQJPdyGSsbTkM8gX1b`)

**Connect to live APIs:** command center, jobs, job creation, talent search/profile/pools, pipeline, interviews, AI interviewer config/results, offers, outreach/communications, company profile, billing (via `/employer/billing`), notifications, settings (members/permissions).

**Do not implement as live (Figma-only / no canonical product API, or forbidden):**

- Employee directory / people operations / performance / L&D / HR onboarding as an HRIS  
- KYC document viewer (never expose KYC)  
- Interview **transcript** tab (raw answers are **never persisted**)  
- Facial/emotion/lie/integrity-as-guilt UI  
- Autonomous screening / auto-hire  
- Workforce planning, compensation intelligence, global talent intelligence as fabricated datasets  
- Tasks/approvals centers unless they map 1:1 to existing routes  

Mark those **COMING / FOUNDATION**. AI assists; human records `/ai-interviews/{id}/decision`.

### Governance / Super Admin — PARTIAL (governance only)

Figma file: [Super Admin Platform](https://www.figma.com/design/M3U75YGTGthQFUJA9azs7w/AskTrabaajo-%E2%80%94-Super-Admin-Platform) (`M3U75YGTGthQFUJA9azs7w`)

**Live to wire:** governance cases, teams, audit, enforcement, appeals (`/admin/governance/*`), finance (`/finance/*` — no UI yet), billing admin views that consume existing finance/billing routes, role-aware nav.

**Figma-only / do not invent APIs:** user 360, company 360, recruiter management, marketing control room, campaigns, tech support diagnostics, government contacts, global workforce map as a live intelligence product. Hide from ordinary users. Least privilege: support ≠ finance ≠ governance.

### Government — FOUNDATION / FUTURE

Figma file: [Government Portal](https://www.figma.com/design/IGQTJOpvt7odmdHjLazDDA/AskTrabaajo---Government-Portal) (`IGQTJOpvt7odmdHjLazDDA`)

~23 designed screens (command center, workforce map, skills, employment, education, industries, investment, tenders, Athena, etc.). **No government frontend exists. No citizen-lookup routes exist.** Backend allows `workforce.aggregates.read` only.

Wave 8: integrate **only** aggregate surfaces that the API actually returns. Label everything else **FOUNDATION** or **FUTURE**. Do not fabricate datasets, endorsements, or individual access. Privacy architecture is aggregate intelligence only.

### Marketing + Careers

Keep. Careers stays on legacy Supabase. Do not restyle the marketing site as a side quest.

---

## 7. Highest-risk integration issues

1. **Dual auth** — public login never creates canonical tokens. Everything else is blocked.  
2. **63-file freeze vs Wave 1** — login, register, root layout, Providers, ConditionalChrome are in the carried tree. Need a narrow owner exception or Wave 1 cannot land.  
3. **15-minute access tokens with no refresh** — even `/id` sessions die quickly.  
4. **Marketing chrome wrapping OS portals** — will make Figma shells look broken.  
5. **No shared org context** — cross-page org drift / wrong-tenant *display* (backend still denies; UI can confuse).  
6. **Athena confirmation bypass temptation** — UI must never auto-confirm. No Athena UI exists yet, so this is a build-time risk.  
7. **Figma > API** — employer HRIS, government intelligence, Super Admin 360s, interview transcripts, KYC. Implementing those as live would invent backend or leak forbidden data.  
8. **Legacy facial-analysis interview** — must not be copied into canonical AI Interview.  
9. **Empty `NEXT_PUBLIC_API_URL`** — silent calls to the Next server.  
10. **Register role field** — sending it would be an invented API.  
11. **Marking mock AI/payments as live** — `AI_PROVIDER=none`, `PAYMENT_PROVIDER=mock`. Degraded mode must be honest.  
12. **Live Supabase** — 21 legacy tables, PITR not confirmed, reconciliation not executed. **Do not touch.**

---

## 8. Recommended implementation order

Match `CURSOR_UI_INTEGRATION_PLAN.md`, with Figma applied **onto already-wired routes**, not as empty visual clones.

| Wave | Work | Why this order |
|---|---|---|
| **0. Exception** | Owner confirms: (a) replace `/login` + `/register` with canonical session; (b) exclude OS routes from marketing chrome. All other 63 files stay frozen. | Process unblocker |
| **1. Foundation** | env, session, refresh, logout, guards, OrgProvider, error/empty/loading, confirmation dialog, portal chrome isolation | Nothing else works without this |
| **1b. Figma shell** | Jobseeker + Employer **app shells** (sidebar, topbar, tokens from Figma component library) wrapping existing pages | Preserve visual identity without rewriting data |
| **2. Jobseeker** | Finish remaining Work ID (privacy/consents/docs), notifications, document requests, bulk-apply exact-ID confirm, empty states | Core “I’m Trabaajo” journey |
| **3. Employer** | Shared org context, jobs/pipeline/talent/offers polish, human-decision UX, billing in employer nav | Tenant isolation UX |
| **4. Athena + AI Interview polish** | New Athena chat with confirmations, tools, usage, degraded mode. Candidate room + employer report already exist | Safety-critical |
| **5. Career Advisor** | Wire `/career-advisor/digest|gaps|paths|opportunities|action-plan`; explainable factors; verified vs unverified | Types already exist |
| **6. Communications** | Shared bell, read/block, no private contact leakage | |
| **7. Governance + finance UI** | RBAC-visible nav; creator/approver separation; `/finance/*` for platform only | |
| **8. Government** | Exists-only aggregates; Figma screens labeled FOUNDATION/FUTURE | |
| **9. UX polish** | Responsive, a11y, MFA/verify-email, session expiry copy, demo against local backend | |

Do not Figma-implement government or Super Admin 360s first. Do not rebuild the backend. Do not start Phase 20.

---

## 9. Files likely to change

**New (preferred — reversible, does not touch the 63):**

- `frontend/.env.example`
- `frontend/src/lib/api/` helpers (register, refresh-retry, domain wrappers)  
- `frontend/src/context/AuthContext.tsx`, `OrgContext.tsx`  
- `frontend/src/components/os/` (guards, portal shells, states, confirm dialog, notification bell)  
- New pages only where API exists and UI is missing: Athena, Career Advisor panels, notifications, privacy/consents, finance (admin), forgot-password  
- This report and later wave notes  

**Existing canonical pages (already committed, safe to evolve):**  
all of `frontend/src/app/jobseeker/**`, `company/**`, `employer/**`, `admin/governance/**`, `id/**` (except do not turn `/id` into a second auth product — fold it into `/login` after Wave 1).

**Needs owner exception (currently in the 63):**

- `frontend/src/app/login/page.tsx`  
- `frontend/src/app/register/page.tsx`  
- `frontend/src/app/layout.tsx`  
- `frontend/src/components/ConditionalChrome.tsx`  
- `frontend/src/components/Providers.tsx`  

---

## 10. Files that MUST NOT change

**Canonical backend (do not rebuild, do not add endpoints, do not weaken authz):**

- `backend/app/**`  
- `backend/alembic/versions/**` (0001–0014)  
- `backend/.env` (untracked secrets)

**Legacy backend + Careers:**

- `backend/main.py`, `backend/api/**`, root `api/**`  
- `frontend/src/app/careers/**`  
- `frontend/src/lib/careers/**`  
- `frontend/src/components/careers/**`

**The 63 carried Phase-1 entries** (current `git status --short` count is 63). Do not stage, commit, or “fix” them. Includes careers, legacy dashboards, `useAuth`, supabase, localAuth, testUser, seed SQL, `supabase-careers-*.sql`, marketing page diffs, etc.

**Forbidden product surface:**

- Anything that reintroduces facial emotion, lie detection, protected-characteristic inference, autonomous hiring  
- Government citizen lookup / individual records  
- Client-side refunds, payment credentials, webhook calls from the browser  
- Hardcoded secrets, copying `backend/.env` into frontend  

**Operational:**

- Do not push  
- Do not execute live reconciliation / `scripts/db/reconcile_legacy_interviews.sql`  
- Do not run Alembic against live Supabase (`zrvrjqwboylvvzusorry`)  
- Do not start Phase 20  

---

## 11. Confirmation — backend is canonical and will not be rebuilt

I have read `CURSOR_HANDOFF.md`, `CURSOR_UI_INTEGRATION_PLAN.md`, `CURSOR_DO_NOT_BREAK.md`, `API_CONTRACT.md`, `FRONTEND_GAP_REPORT.md`, `PHASE_19_FINAL_HANDOFF.md`, and `PROJECT_STATUS.json`, then verified them against the repo.

**Understood and binding:**

- The platform through Phase 19 is the source of truth: 246 `/api/v1` routes, 80 canonical tables, UUID identity, Work ID, RBAC, RLS, Athena confirmation gates, AI Interview safety model, commerce mock provider, governance/enforcement.  
- Staging E2E already passed: auth → org → AI interview → report → human decision → billing boundary → cross-tenant denial.  
- Live reconciliation is **not** executed and is **out of scope**.  
- Frontend work **consumes** `/api/v1` through `frontend/src/lib/api/`. It does not create a second backend, auth system, database model, RBAC model, or Work ID.  
- If a Figma screen has no canonical route, the UI shows a polished “not yet available” state. It does not invent APIs.  
- Visual work preserves AskTrabaajo identity (Figma portals + existing gold brand). Proof shells are temporary. Careers stays untouched.

**How we turn the existing UI into the product:**

```
Wave 1: one canonical session
     → existing proof pages start working for a real logged-in user
     → Figma shells wrap those pages
     → remaining API gaps filled screen-by-screen
     → Figma-only / future / forbidden screens stay labeled, never faked
```

A screen is integrated only when: **UI → API → auth → authorization → real backend state → loading/empty/error → security boundary.** Looking good is not done.

---

*Next action (after owner reads this): Wave 1, starting with the login/register + chrome exceptions, then canonical session + refresh + guards. No deploy. No live DB. No backend rebuild.*
