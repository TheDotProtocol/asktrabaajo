# FRONTEND GAP REPORT — Current UI vs Canonical Backend

Audit performed at the Phase 19 freeze by scanning `frontend/src` (no UI changes made during the audit).

## How the frontend is organized today

- **Canonical client layer exists:** `src/lib/api/client.ts` (`ApiClient` — base `NEXT_PUBLIC_API_URL + /api/v1`, bearer token, error envelope), `session.ts` (localStorage tokens `asktrabaajo_at`/`asktrabaajo_rt`, `api` singleton, `fetchMe`, `login`, `logout`), `types.ts`. **29 page files already import `lib/api`** and call real canonical endpoints.
- **Legacy auth layer still present:** `src/hooks/useAuth.ts` (Supabase + `localAuth.ts` local-session fallback + `testUser.ts`), `src/lib/supabase.ts`, `src/lib/supabaseStorage.ts`. Used by **8 page files**: `login`, `register`, `dashboard/*`, `interviews`, `interview/*`.
- **Legacy careers layer:** `src/lib/careers/*` (api.ts, aiApi.ts, employerApi.ts, supabase.ts, types.ts, constants.ts) + `src/app/careers/*` pages — **separate data source; DO NOT TOUCH**.
- **No raw `fetch()` calls** in app pages (everything goes through the api client, the careers client, or supabase libs).

## Category-by-category gaps

### 1. Authentication — DUAL AUTH GAP (highest priority)
| Item | State |
|---|---|
| Canonical login/register API | ✅ exists (`/api/v1/auth/login`, `/register`, `lib/api/session.ts#login`) |
| Login/register pages | ⚠️ **use legacy `useAuth`** (Supabase/local) — they do NOT write the canonical `asktrabaajo_at` token, so canonical pages have no session after login |
| Session persistence | ⚠️ canonical tokens in localStorage (`session.ts`); refresh/rotation handler not wired (`ApiClient.onUnauthorized` only clears) |
| Route guards / redirects | ❌ none — pages assume a token exists; no shared guard component |
| Logout | ⚠️ canonical `logout()` exists in `session.ts`; not wired into a shared nav |
| MFA / verify-email UX | ❌ backend exists, no UI |

**Fix (Wave 1):** make login/register write the canonical session (`setSession`), add refresh handling + 401 auto-refresh, add route guards, wire logout, keep `useAuth` only for legacy/careers surfaces.

### 2. Identity / Work ID
| Item | State |
|---|---|
| Work ID pages | ⚠️ `src/app/id/work-id/page.tsx`, `src/app/id/page.tsx` call canonical API — partially integrated |
| Profile/skills/experience/education/credentials editing | ⚠️ backend routes exist (`/work-id/*`); verify every screen maps to them; credentials verification-state display needs truthful rendering |
| Consents / privacy | ⚠️ backend exists (`/work-id/consents`, `/work-id/privacy`); UI coverage uncertain |

### 3. Jobseeker portal — most integrated
| Item | State |
|---|---|
| Pages | ✅ `jobseeker/*` (dashboard, opportunities, applications, offers, interviews, interview-prep, career, work-dna, communications, ai-interview) all import `lib/api` |
| Data wiring | ⚠️ mostly real API; audit each page for leftover mock/local state (`jobseeker/interview-prep` has mock/local behavior) |
| Bulk apply confirmation | ⚠️ `/jobseeker/applications/batch` is high-risk; UI must show exact-ID confirmation |
| Loading/error/empty states | ❌ largely missing (pages use plain useState/useEffect) |
| Notifications | ⚠️ backend exists; no polling/subscription UI |

### 4. Employer / Company
| Item | State |
|---|---|
| Pages | ✅ `company/*` (dashboard, jobs, candidates, pipeline, communications) + `employer/ai-interviews` + `employer/billing` import `lib/api` |
| Org context | ⚠️ pages fetch `/organizations` and pick `organization_id` per page; **no shared org selector/context** — introduce in Wave 1 |
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
| Career Advisor | ⚠️ `jobseeker/career` exists; verify digest/gaps/paths/opportunities/action-plan screens |
| Interview Prep | ⚠️ page exists; confirm mock/local bits removed or clearly labeled |
| AI Interview candidate room | ✅ `jobseeker/ai-interview` (lobby→consent→room→feedback) via canonical API with `X-Interview-Token` |

### 7. Communications / notifications
| Item | State |
|---|---|
| Messaging | ⚠️ `jobseeker/communications` + `company/communications` exist; verify read/close/block wiring |
| Notifications | ⚠️ no shared notification bell/polling |

### 8. Commerce
| Item | State |
|---|---|
| Billing dashboard | ✅ `employer/billing` |
| Plan/entitlements/usage/invoices | ⚠️ backend routes exist; partial UI |
| Payment status | ✅ safe (mock); never build client-side refund/payment authority |

### 9. Missing cross-cutting surfaces
- ❌ Shared nav/shell per portal (jobseeker layout, company layout exist but thin; no auth-aware nav)
- ❌ Route guards + RBAC-aware navigation (hide routes the user's roles can't access)
- ❌ Loading skeletons / error states / empty states
- ❌ Toast/confirmation-dialog system (needed for Athena confirmations, bulk apply, high-risk actions)
- ❌ Org-context selector for employer/admin surfaces
- ❌ Responsive/mobile pass and accessibility pass (keyboard, ARIA)
- ❌ `.env` guidance: `NEXT_PUBLIC_API_URL` documented in `.env.example` (no secrets)

## Status legend applied

| Status | Where |
|---|---|
| **READY TO INTEGRATE** (backend + client exist; page to be built/connected) | Athena chat, notifications bell, MFA/verify-email UI, org selector, shared nav, loading/error/empty states |
| **PARTIALLY INTEGRATED** | jobseeker/*, company/*, admin/governance/*, employer/*, id/* (verify each call; remove mock/local leftovers) |
| **UI EXISTS / API NOT CONNECTED** | none found (all audited pages either call canonical API or are explicitly legacy) |
| **API EXISTS / UI MISSING** | Athena chat, MFA, verify-email, notifications, usage/entitlements detail, document requests detail |
| **BLOCKED** | live DB anything, provider-dependent features (voice/video, real payments), government citizen surfaces (forbidden) |
| **LEGACY — DO NOT TOUCH** | `careers/*`, `dashboard/*`, `interviews/*`, `interview/*`, `login`/`register` (until Wave 1 replaces), `lib/careers/*`, `lib/supabase*`, `hooks/useAuth` (until superseded) |

## Priority order (matches `CURSOR_UI_INTEGRATION_PLAN.md`)

1. **Wave 1 foundation** — dual-auth bridge, refresh handling, route guards, org context, shared UI primitives.
2. **Wave 2–3** — finish wiring jobseeker + employer journeys (remove mocks, add states).
3. **Wave 4** — Athena chat + confirmations, career advisor, prep, AI interview polish.
4. **Waves 5–9** — communications, governance, commerce polish, government (exists-only), final UX.