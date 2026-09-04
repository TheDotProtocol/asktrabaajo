# FRONTEND GAP REPORT — Current UI vs Canonical Backend

Audit performed at the Phase 19 freeze by scanning `frontend/src` (no UI changes made during the audit).

**Wave 1 update (2026-09-05):** the dual-auth gap is closed for the canonical application. `/login` and `/register` write `asktrabaajo_at` / `asktrabaajo_rt` via `POST /api/v1/auth/*`. `ApiClient` rotates refresh tokens on 401 (single-flight). `PortalGuard` + `OsChrome` + `OrgProvider` wrap jobseeker / company / employer / admin / identity. `useAuth` remains **only** on legacy Careers + `/dashboard` + `/interview*` — do not use it for canonical pages. See `CURSOR_WAVE_1_REPORT.md`.

**Wave 1 closure (2026-09-05):** Wave 1 is **ACCEPTED**. The new public flagship site is a separate Emergent repo (`https://github.com/TheDotProtocol/trabaajowebsite`) — marketing SPA, no canonical auth. Do not merge it into this app. CTA wiring and Wave 2 sequence: `CURSOR_WAVE_1_CLOSURE.md` + `CURSOR_WAVE_2_READINESS.md`.

**Wave 2 update (2026-09-05):** Candidate Figma shell + Jobseeker Employment OS are wired to canonical `/api/v1`. Dashboard, Work ID, documents, credentials, Work DNA, career goals, Career Advisor (`/career-advisor/*`), opportunities (including match modes), applications, interviews, AI Interview, interview prep, offers, communications, notifications, and privacy/settings are API-backed with empty states. No mock APIs. Hosted DB untouched — see `CURSOR_WAVE_2_CLOSURE.md`.

**Wave 3 update (2026-09-05):** Employer / HR Figma shell (`EmployerShell`) + Company Employment OS are wired to canonical `/api/v1`. Command center, profile, members/RBAC, jobs (including multi-step draft + clone-as-template), Talent Graph, pipeline, interviews, AI interviews + human decision, offers, communications, analytics, notifications, billing, and settings are API-backed. Offices/departments/job-template catalogs have **no first-class API** and are not invented. Hosted DB untouched — see `CURSOR_WAVE_3_CLOSURE.md`.

**Wave 4 update (2026-09-05):** Athena workspace is a real `/api/v1/athena/*` client for Candidate and Employer. No Athena Figma — designed from the OS design system. `GET /athena/status` drives honest degraded mode. High-risk actions use exact-scope confirmation. Session history is not an API. Hosted DB untouched — see `CURSOR_WAVE_4_CLOSURE.md`.

**Wave 4 refinement (2026-09-05):** Athena workspace polish only — context band, first-use starters, native result cards, named confirmation, honest processing states, dedicated mobile layout, additional allowlisted Ask Athena links (Applications, Interviews, Work ID, Jobs). No Wave 5. No backend rewrite. See `CURSOR_ATHENA_DESIGN_DECISIONS.md` §18.

**Wave 5 update (2026-09-05):** Super Admin Figma shell (`AdminShell`) + platform command center, governance, enforcement, appeals, audit, teams, finance, support (honesty), operations, notifications, and settings are wired to canonical `/api/v1`. Least privilege in nav; backend remains authoritative. Figma People/Companies/Governments/Marketing directories and platform Athena tools were **not** fabricated. Hosted DB untouched — see `CURSOR_WAVE_5_CLOSURE.md` and `CURSOR_ADMIN_DESIGN_DECISIONS.md`.

**Wave 6 update (2026-09-05):** Localhost QA. Isolated SQLite + Playwright opened every implemented portal. Login/register restyled to the Candidate Figma split-screen and removed from marketing chrome. Not pixel-perfect. Government still absent. See `CURSOR_WAVE_6_CLOSURE.md`.

**Wave 7 update (2026-09-05):** Public website (`TheDotProtocol/trabaajowebsite`) is the local landing page on :3001. CTAs resolve through `REACT_APP_CANONICAL_APP_URL` to the canonical app. `/portals` picks Jobseeker / Employer / Government from real memberships. `/government` is an honesty foundation page — no fabricated intelligence. See `CURSOR_WAVE_7_CLOSURE.md`.

## How the frontend is organized today

- **Canonical client layer exists:** `src/lib/api/client.ts` (`ApiClient` — base `NEXT_PUBLIC_API_URL + /api/v1`, bearer token, error envelope), `session.ts` (localStorage tokens `asktrabaajo_at`/`asktrabaajo_rt`, `api` singleton, `fetchMe`, `login`, `logout`), `types.ts`. **29 page files already import `lib/api`** and call real canonical endpoints.
- **Legacy auth layer still present for Careers/legacy only:** `src/hooks/useAuth.ts` (Supabase + `localAuth.ts` + `testUser.ts`). Used by `/dashboard/*`, `/interviews`, `/interview/*`, careers nav — **not** by `/login` or `/register` after Wave 1.
- **Legacy careers layer:** `src/lib/careers/*` (api.ts, aiApi.ts, employerApi.ts, supabase.ts, types.ts, constants.ts) + `src/app/careers/*` pages — **separate data source; DO NOT TOUCH**.
- **No raw `fetch()` calls** in app pages (everything goes through the api client, the careers client, or supabase libs).

## Category-by-category gaps

### 1. Authentication — Wave 1 complete for the canonical app
| Item | State |
|---|---|
| Canonical login/register API | ✅ `/api/v1/auth/login`, `/register`, `session.ts` |
| Login/register pages | ✅ write canonical tokens; redirect via `homeForMe` / `?next=` |
| Session persistence | ✅ localStorage `asktrabaajo_at` / `asktrabaajo_rt`; restore on reload |
| Refresh | ✅ `POST /auth/refresh` rotation, single-flight, retry-then-clear |
| Route guards / redirects | ✅ `PortalGuard` on jobseeker / company / employer / admin / id |
| Logout | ✅ shell + `POST /auth/logout` + `clearSession` |
| MFA on login | ✅ challenge step when `mfa_required` |
| Forgot password | ✅ `/forgot-password` → `POST /auth/forgot-password` |
| MFA enroll / verify-email polish | ⚠️ backend exists; `/id` can send verification; enroll UI still Wave 9 |

`useAuth` stays for legacy/careers surfaces only.

### 2. Identity / Work ID
| Item | State |
|---|---|
| Work ID pages | ✅ `/id/work-id` Candidate-styled; `/id` account/security |
| Profile/skills/experience/education/credentials editing | ✅ canonical `/work-id/*`; StatusPill for verification states |
| Consents / privacy | ✅ `/jobseeker/privacy` → `GET/PUT /work-id/privacy` in plain language |

### 3. Jobseeker portal — Wave 2 Candidate OS
| Item | State |
|---|---|
| Shell | ✅ `CandidateShell` (Figma tokens, nav, unread badge) |
| Pages | ✅ dashboard, Work ID, documents, credentials, Work DNA, career, opportunities, applications, interviews, AI interview, interview-prep, offers, communications, notifications, privacy, Athena entry |
| Data wiring | ✅ `lib/api` only; Career Advisor modes from `/career-advisor/opportunities` |
| Bulk apply confirmation | ✅ exact selected-count confirmation before `POST /applications/batch` |
| Loading/error/empty states | ✅ shared `EmptyState` / `ErrorBanner` / `LoadingState` on major Candidate screens |
| Notifications | ✅ `/jobseeker/notifications` + header unread count |

### 4. Employer / Company — Wave 3 Employer OS
| Item | State |
|---|---|
| Shell | ✅ `EmployerShell` (HR Figma tokens, org switcher, unread badge, mobile drawer) |
| Pages | ✅ dashboard, profile, members, jobs, jobs/new, candidates, pipeline, interviews, offers, analytics, communications, notifications, settings, athena (Soon), `/employer/ai-interviews`, `/employer/billing` |
| Data wiring | ✅ `lib/api` only; no mock APIs; no invented production stats |
| Org context | ✅ `OrgProvider` + shell selector (`asktrabaajo_org_id`); backend membership remains authoritative |
| Billing | ✅ `/employer/billing` self-service via canonical API (mock provider; no client payment authority) |
| AI reports | ✅ `/employer/ai-interviews` + explicit human `/decision` |
| Offices / departments / templates | ⚠️ no first-class APIs — HQ = profile city/country; departments = distinct `job.department`; templates = clone job as draft |
| Workforce / planning / onboarding Figma | ❌ no product APIs — not fabricated |

### 5. Admin / Governance — Wave 5 Super Admin
| Item | State |
|---|---|
| Shell | ✅ `AdminShell` (Figma tokens, 240px sidebar, Development badge, permission-filtered nav) |
| Pages | ✅ command center, governance, enforcement, appeals, audit, teams, finance, support, operations, athena (unavailable), notifications, settings |
| Data wiring | ✅ `lib/api` only; truthful counts; no invented metrics |
| Role separation UX | ✅ nav gated by permission; finance hidden without `finance.read`; support cannot refund; creator≠approver is server-enforced |
| People / Companies / Governments | ❌ no platform directory APIs — not fabricated |
| Support tickets | ❌ no ticket API — honesty page only |

### 6. AI surfaces
| Item | State |
|---|---|
| Athena chat | ✅ `/jobseeker/athena` + `/company/athena` via `/api/v1/athena/*`. Degraded when `AI_PROVIDER=none`. History list not in API. |
| Career Advisor | ✅ `jobseeker/career` uses `/jobseeker/advisor`, intelligence, goals, and `/career-advisor/{gaps,paths,opportunities,action-plan}` |
| Interview Prep | ⚠️ page exists; confirm mock/local bits removed or clearly labeled |
| AI Interview candidate room | ✅ `jobseeker/ai-interview` (lobby→consent→room→feedback) via canonical API with `X-Interview-Token` |

### 7. Communications / notifications
| Item | State |
|---|---|
| Messaging | ✅ Candidate + Employer communications via canonical talent/jobseeker APIs |
| Notifications | ✅ Candidate and Employer header badge + notification center (user-scoped `/jobseeker/notifications`) |

### 8. Commerce
| Item | State |
|---|---|
| Billing dashboard | ✅ `employer/billing` |
| Plan/entitlements/usage/invoices | ⚠️ backend routes exist; partial UI |
| Payment status | ✅ safe (mock); never build client-side refund/payment authority |

### 9. Missing cross-cutting surfaces
- ✅ Shared functional OS shell (`OsChrome`) with logout, portal links, org selector
- ✅ Route guards + permission-aware nav (backend remains authoritative)
- ✅ Candidate page-level loading/error/empty states (Wave 2)
- ✅ Employer page-level loading/error/empty states (Wave 3)
- ✅ Athena confirmation dialog (exact-scope, backend-authoritative)
- ✅ Org-context selector (`OrgProvider`, `asktrabaajo_org_id`)
- ❌ Responsive/mobile pass and accessibility pass (keyboard, ARIA)
- ✅ `.env` guidance: `frontend/.env.example` + `.env.development` (`NEXT_PUBLIC_API_URL` only)

## Status legend applied

| Status | Where |
|---|---|
| **READY TO INTEGRATE** (backend + client exist; page to be built/connected) | MFA enroll polish |
| **PARTIALLY INTEGRATED** | employer billing entitlements/usage detail |
| **UI EXISTS / API NOT CONNECTED** | none found on Candidate OS |
| **API EXISTS / UI MISSING** | Athena session history, MFA enroll, usage/entitlements detail |
| **BLOCKED** | live DB anything, provider-dependent features (voice/video, real payments), government citizen surfaces (forbidden) |
| **LEGACY — DO NOT TOUCH** | `careers/*`, `dashboard/*`, `interviews/*`, `interview/*`, `lib/careers/*`, `lib/supabase*`, `hooks/useAuth` (Careers/legacy only) |

## Priority order (matches `CURSOR_UI_INTEGRATION_PLAN.md`)

1. **Wave 1 foundation** — ✅ dual-auth bridge, refresh, guards, org context, functional shell.
2. **Wave 2** — ✅ Candidate Figma shell + Jobseeker Employment OS.
3. **Wave 3** — ✅ Employer / Company Figma OS (`CURSOR_WAVE_3_CLOSURE.md`).
4. **Wave 4** — ✅ Athena UI (`CURSOR_WAVE_4_CLOSURE.md`, `CURSOR_ATHENA_DESIGN_DECISIONS.md`).
5. **Wave 5** — ✅ Super Admin control plane (`CURSOR_WAVE_5_CLOSURE.md`).
6. **Waves 6–9** — communications/commerce polish, government (exists-only), final UX. See `CURSOR_WAVE_6_READINESS.md`. Do not start without a separate approval.