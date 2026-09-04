# FRONTEND GAP REPORT — Current UI vs Canonical Backend

Audit performed at the Phase 19 freeze by scanning `frontend/src` (no UI changes made during the audit).

**Wave 1 update (2026-09-05):** the dual-auth gap is closed for the canonical application. `/login` and `/register` write `asktrabaajo_at` / `asktrabaajo_rt` via `POST /api/v1/auth/*`. `ApiClient` rotates refresh tokens on 401 (single-flight). `PortalGuard` + `OsChrome` + `OrgProvider` wrap jobseeker / company / employer / admin / identity. `useAuth` remains **only** on legacy Careers + `/dashboard` + `/interview*` — do not use it for canonical pages. See `CURSOR_WAVE_1_REPORT.md`.

**Wave 1 closure (2026-09-05):** Wave 1 is **ACCEPTED**. The new public flagship site is a separate Emergent repo (`https://github.com/TheDotProtocol/trabaajowebsite`) — marketing SPA, no canonical auth. Do not merge it into this app. CTA wiring and Wave 2 sequence: `CURSOR_WAVE_1_CLOSURE.md` + `CURSOR_WAVE_2_READINESS.md`.

**Wave 2 update (2026-09-05):** Candidate Figma shell + Jobseeker Employment OS are wired to canonical `/api/v1`. Dashboard, Work ID, documents, credentials, Work DNA, career goals, Career Advisor (`/career-advisor/*`), opportunities (including match modes), applications, interviews, AI Interview, interview prep, offers, communications, notifications, and privacy/settings are API-backed with empty states. No mock APIs. Hosted DB untouched — see `CURSOR_WAVE_2_CLOSURE.md`.

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

### 4. Employer / Company
| Item | State |
|---|---|
| Pages | ✅ `company/*` (dashboard, jobs, candidates, pipeline, communications) + `employer/ai-interviews` + `employer/billing` import `lib/api` |
| Org context | ✅ `OrgProvider` + shell selector (`asktrabaajo_org_id`); pages read `useOrg()`. Backend membership checks remain authoritative. |
| Billing | ✅ `/employer/billing` is read-only self-service via canonical API (mock provider; no client payment authority — correct) |
| Candidate reports | ⚠️ AI interview report screen exists (`employer/ai-interviews`) — verify human-decision flow (`/decision`) |

### 5. Admin / Governance
| Item | State |
|---|---|
| Pages | ✅ `admin/governance/*` (cases, enforcement, appeals, audit, teams) import `lib/api` |
| Role separation UX | ⚠️ enforce creator/approver separation in UI; hide finance from support; governance vs finance vs support permission-aware nav needed |

### 6. AI surfaces
| Item | State |
|---|---|
| Athena chat | ❌ no canonical Athena UI (careers-era `ai` chat is legacy). Wave 4: Athena chat + confirmations + tools/usage display |
| Career Advisor | ✅ `jobseeker/career` uses `/jobseeker/advisor`, intelligence, goals, and `/career-advisor/{gaps,paths,opportunities,action-plan}` |
| Interview Prep | ⚠️ page exists; confirm mock/local bits removed or clearly labeled |
| AI Interview candidate room | ✅ `jobseeker/ai-interview` (lobby→consent→room→feedback) via canonical API with `X-Interview-Token` |

### 7. Communications / notifications
| Item | State |
|---|---|
| Messaging | ⚠️ `jobseeker/communications` + `company/communications` exist; verify read/close/block wiring |
| Notifications | ✅ Candidate header badge + notification center (no invented records) |

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
- ⚠️ Employer page-level empty states remain Wave 3
- ❌ Toast/confirmation-dialog system (needed for Athena confirmations, bulk apply, high-risk actions)
- ✅ Org-context selector (`OrgProvider`, `asktrabaajo_org_id`)
- ❌ Responsive/mobile pass and accessibility pass (keyboard, ARIA)
- ✅ `.env` guidance: `frontend/.env.example` + `.env.development` (`NEXT_PUBLIC_API_URL` only)

## Status legend applied

| Status | Where |
|---|---|
| **READY TO INTEGRATE** (backend + client exist; page to be built/connected) | Athena chat, MFA enroll polish, employer Figma shell |
| **PARTIALLY INTEGRATED** | company/*, admin/governance/*, employer/* (Wave 3+) |
| **UI EXISTS / API NOT CONNECTED** | none found on Candidate OS |
| **API EXISTS / UI MISSING** | Athena chat, MFA enroll, usage/entitlements detail |
| **BLOCKED** | live DB anything, provider-dependent features (voice/video, real payments), government citizen surfaces (forbidden) |
| **LEGACY — DO NOT TOUCH** | `careers/*`, `dashboard/*`, `interviews/*`, `interview/*`, `lib/careers/*`, `lib/supabase*`, `hooks/useAuth` (Careers/legacy only) |

## Priority order (matches `CURSOR_UI_INTEGRATION_PLAN.md`)

1. **Wave 1 foundation** — ✅ dual-auth bridge, refresh, guards, org context, functional shell.
2. **Wave 2** — ✅ Candidate Figma shell + Jobseeker Employment OS.
3. **Wave 3** — Employer / Company Figma OS (`CURSOR_WAVE_3_READINESS.md`).
4. **Wave 4** — Athena chat + confirmations.
5. **Waves 5–9** — communications, governance, commerce polish, government (exists-only), final UX.