# CURSOR WAVE 1 REPORT — Canonical authentication + session + app foundation

**Date:** 2026-09-05  
**Status:** COMPLETE for Wave 1 scope. Stop here — do not start Wave 2, Figma portals, Athena, Government, deploy, or live Supabase.

```
REGISTER / LOGIN
    → POST /api/v1/auth/register|login
    → asktrabaajo_at + asktrabaajo_rt
    → AuthProvider (GET /auth/me)
    → PortalGuard
    → OsChrome (role/org/logout)
    → canonical page
    → /api/v1
    → real backend JSON
```

---

## What changed

Wave 1 removed the dual-auth problem for the AskTrabaajo application:

- Public `/login` and `/register` call the canonical FastAPI auth contract.
- One session (`asktrabaajo_at` / `asktrabaajo_rt`).
- Access-token expiry triggers `POST /auth/refresh` (rotating refresh, single-flight) then retries the original request.
- Failed refresh clears the session and the guard sends the user to `/login`.
- Jobseeker, company, employer, admin, and identity routes are guarded.
- Organization selection is shared (`OrgProvider`, same `asktrabaajo_org_id` key the company pages already used).
- Functional OS shell (not Figma) with logout, portal links, and org switcher.
- Marketing chrome no longer wraps OS portals.
- Legacy Careers / `useAuth` / dashboards / interviews were not migrated.

Register still shows the visual “I am a…” cards but **does not send a role**. Canonical register is `{ email, password, full_name }` only. Employer intent only affects post-login routing (`/company`), where the user can create an organization.

---

## Frozen-file exceptions used

Authorized narrow exception. Only these carried Phase-1 files were edited:

| File | Why it had to change | What changed |
|---|---|---|
| `frontend/src/app/login/page.tsx` | Public login wrote a legacy Supabase/local session, so canonical pages never received a token. | Same gold UI; submit → `useCanonicalAuth().login` / MFA verify; redirect via `homeForMe`. Removed `useAuth` and test-user prefill. |
| `frontend/src/app/register/page.tsx` | Same dual-auth gap on sign-up. | Same gold UI; submit → `POST /auth/register` with `full_name`; role cards are UX intent only. |
| `frontend/src/app/layout.tsx` | HEAD always mounted marketing Header/Footer and had no provider tree, so AuthProvider could not wrap the app. | Wraps `Providers` + `ConditionalChrome`. Theme bootstrap script preserved from the Phase-1 working tree. |
| `frontend/src/components/Providers.tsx` | Needed a single Auth + Org provider tree. | Theme → Auth → Org. |
| `frontend/src/components/ConditionalChrome.tsx` | Marketing Header/Footer wrapped OS portals. | Added `/jobseeker`, `/company`, `/employer`, `/admin`, `/id`, `/forbidden` to standalone prefixes. Careers/dashboard prefixes unchanged. |
| `frontend/src/components/Logo.tsx` + `frontend/src/lib/brand.ts` | Login/register/chrome already imported these Phase-1 files. | Committed as-is so the auth pages keep their existing mark. No auth logic. |
| `frontend/src/context/ThemeContext.tsx` | `Providers` already wraps `ThemeProvider`. | Committed so the provider tree mounts. Not an auth system. |

`useAuth.ts` was **not** modified for Wave 1 (Careers/legacy still need it; leftover Phase-1 edits remain unstaged).

---

## Authentication architecture

Canonical only for the product:

| Step | Contract |
|---|---|
| Register | `POST /api/v1/auth/register` → `TokenPair` (201) |
| Login | `POST /api/v1/auth/login` → tokens or `{ mfa_required, mfa_token }` |
| MFA | `POST /api/v1/auth/mfa/verify` |
| Me | `GET /api/v1/auth/me` (user, person, memberships, permissions, super_admin) |
| Logout | `POST /api/v1/auth/logout` `{ refresh_token }` then `clearSession()` |

Frontend entry: `AuthProvider` (`frontend/src/context/AuthContext.tsx`) + `session.ts`.

---

## Session architecture

- Keys unchanged: `asktrabaajo_at`, `asktrabaajo_rt` in `localStorage` (existing canonical keys; required for reload restore).
- `subscribeSession` notifies `AuthProvider` to re-hydrate `GET /auth/me`.
- No Supabase session, no `localAuth`, no second token format.
- Network errors during `/auth/me` do **not** wipe tokens (avoids random logout).

---

## Refresh architecture

Matches `refresh_access_token` in the backend (rotate; replay of a revoked refresh kills the family):

1. Canonical request returns 401.
2. Auth endpoints (`/auth/login|register|refresh|logout|mfa/verify|forgot-password|reset-password`) do **not** retry.
3. Other paths: single-flight `POST /auth/refresh` with the current refresh token (raw fetch, not through the retrying client).
4. Success → store new pair → retry original request once.
5. Invalid refresh (401) → `clearSession` → caller sees unauthorized → guard redirects to `/login`.
6. Network failure on refresh → tokens kept; request fails with a network/401 error rather than a silent wipe.

---

## Route guard architecture

`PortalGuard` (`allow`: `authenticated` | `employer` | `governance`):

- Loading: “Restoring your session…”
- No session: `/login?next=<path>`
- Network error with stored tokens: visible error, not a blank screen
- Signed in but failing the allow check: in-place 403 copy (no data fetch in the guard)

Applied in layouts:

- `/jobseeker/*`, `/id/*` → authenticated
- `/company/*`, `/employer/*` → authenticated (so a new user can create an org on `/company`; backend still 403s org-scoped data)
- `/admin/*` → governance permissions from `/auth/me`

---

## RBAC integration

No frontend permission catalog. `me.permissions` and `me.super_admin` from the API.

`hasPermission` / `hasAnyPermission` in `portal.ts` only hide nav. `OsChrome` hides company/admin items that the user lacks. Hitting a URL still goes to the page; the **backend** returns 403.

Governance nav permissions: `reports.read`, `enforcement.read`, `appeals.read`, `reports.teams`, `platform.audit.read`, `admin.manage`. Super admin sees all.

---

## Organization context

`OrgProvider`:

- Employer/recruiter memberships from `me.memberships` (not a client-invented org id).
- Persists selection as `asktrabaajo_org_id` (same key company pages already used).
- Validates stored id against current memberships; otherwise first membership.
- Company/employer pages read `useOrg().organizationId`.
- Backend still checks membership on every `/company/{org}` and `/talent/{org}` call.

---

## API client

`frontend/src/lib/api/client.ts`:

- Default origin `http://localhost:8000` if `NEXT_PUBLIC_API_URL` is unset (documented in `.env.example` / `.env.development`).
- JSON error envelope → `ApiError`.
- `network_error` on fetch failure.
- Refresh-then-retry as above.
- Existing `api.get/post/put/patch/delete` signatures unchanged; canonical pages keep importing `api` from `session.ts`.

---

## Legacy auth dependencies removed (canonical app only)

Removed from `/login` and `/register`: `useAuth`, `TEST_USER` prefill, Supabase sign-in/sign-up.

**Left in place (Careers / legacy product):** `useAuth.ts`, `localAuth.ts`, `testUser.ts`, `lib/supabase.ts`, `/dashboard/*`, `/interviews`, `/interview/*`, `lib/careers/*`.

`/id` is no longer a second login form; it is account settings behind `PortalGuard`.

---

## Files changed

**New**

- `frontend/src/lib/api/portal.ts`
- `frontend/src/lib/api/org.ts`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/context/OrgContext.tsx`
- `frontend/src/components/os/PortalGuard.tsx`
- `frontend/src/components/os/OsChrome.tsx`
- `frontend/src/app/employer/layout.tsx`
- `frontend/src/app/id/layout.tsx`
- `frontend/src/app/forgot-password/page.tsx`
- `frontend/src/app/forbidden/page.tsx`
- `frontend/src/components/Logo.tsx`
- `frontend/src/lib/brand.ts`
- `frontend/src/context/ThemeContext.tsx`
- `scripts/wave1_auth_e2e.py`
- `scripts/wave1_portal_test.mjs`
- `CURSOR_WAVE_1_REPORT.md`

**Updated (canonical / docs)**

- `frontend/.env.example` (API origin default; Legacy Careers keys kept as empty placeholders)
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/session.ts`
- `frontend/src/app/layout.tsx`
- layouts: `jobseeker`, `company`, `admin`
- company pages (org context): `page`, `jobs`, `pipeline`, `communications`, `candidates`, `candidates/[id]`
- `employer/ai-interviews`, `employer/billing`
- `id/page.tsx`
- `FRONTEND_GAP_REPORT.md`
- `CURSOR_INTEGRATION_START_REPORT.md`

**Frozen exceptions:** see table above.

**Not changed:** `backend/app/**`, migrations, live `.env`, careers, `useAuth`, dashboard/interview legacy.

Local `frontend/.env.development` (`NEXT_PUBLIC_API_URL` only) exists for developers; `frontend/.gitignore` ignores `.env*` so it is not committed. The client already defaults to `http://localhost:8000`.

---

## Tests

| Suite | Result |
|---|---|
| `npx tsc --noEmit` | PASS |
| `npx eslint src` | PASS — 0 errors, 5 pre-existing careers warnings |
| `npm run build` | PASS (Next.js 15.5.4) |
| `pytest tests_phase3` | PASS (baseline green; 11 skipped) |
| `python scripts/wave1_auth_e2e.py` | **WAVE1 AUTH E2E: PASS** |
| `node scripts/wave1_portal_test.mjs` | PASS |

E2E (isolated sqlite TestClient — **not** live Supabase):

1. registration → token pair  
2. login  
3. invalid login → 401  
4. `GET /auth/me` + person  
5. refresh rotates  
6. refresh replay → 401  
7. invalid refresh → 401  
8. logout revokes refresh  
9. `GET /jobseeker/dashboard` with token  
10. same without token → 401  
11. employer `GET /finance/transactions` → 403  
12. create org + company dashboard  
13. other user → 403 on that org  
Plus representative page APIs: opportunities, applications, interviews, offers, work-dna, communications, work-id, jobs, pipeline, talent search, AI interviews, billing plans, governance 403.

Browser click-through of `/login` against a running UI was not executed in this pass (no browser session). The production build includes `/login`, `/register`, `/jobseeker`, `/company`, `/id`, governance, billing, and AI interview routes.

---

## Known limitations / remaining Wave-1 issues

- Access tokens remain in `localStorage` (same as the prior canonical client). Refresh rotation is now wired; httpOnly cookies would need a backend change (out of scope).
- MFA **enrollment** UI is not a product screen; login MFA challenge is implemented. Verify-email send exists on `/id`.
- Company layout is `authenticated` so a brand-new employer can create an org. Nested company APIs are still backend-enforced.
- Functional shell is not the Figma Candidate/HR design.
- Canonical pages still have thin loading/empty states (Wave 2+).
- Local `backend/.env` still points at live Supabase if used as-is. Wave 1 tests **override** `DATABASE_URL=sqlite://` and never used that file. Operators should run the canonical app against sqlite/scratch PG, not live.

---

## Recommended Wave 2

Jobseeker OS polish on the now-working session: Work ID privacy/consents, notifications, document requests, bulk-apply exact-ID confirmation, empty/error states on existing jobseeker pages. Do not start Figma portal replacement, Athena chat, Career Advisor `/career-advisor/*`, or Government.

Do not deploy. Do not push. Do not touch live Supabase.
