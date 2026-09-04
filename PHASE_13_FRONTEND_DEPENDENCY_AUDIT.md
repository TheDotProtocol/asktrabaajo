# PHASE 13 — FRONTEND DEPENDENCY AUDIT

Scope: every remaining frontend dependency on Supabase (client, auth,
direct table access, storage) and on legacy endpoints, with a
classification and the cutover plan. **No frontend code was changed in
Phase 13** — this is the audit the brief requires so the next phase can
cut over safely without breaking the live Careers platform.

## Supabase dependency inventory

| File | Dependency | Classification |
|---|---|---|
| `src/lib/supabase.ts` | `createClient` from `@supabase/supabase-js` (browser client, anon key) | LEGACY COMPAT — careers read path; also the shared client for auth pages |
| `src/lib/careers/supabase.ts` | re-exports the client | LEGACY COMPAT |
| `src/lib/careers/api.ts` | `supabase.from('offices'/'saved_jobs' …)` direct reads/writes | LEGACY COMPAT — careers public data + saved-jobs (user-scoped, RLS-guarded) |
| `src/lib/careers/employerApi.ts` | `supabase.from('jobs'/'job_templates' …)` employer writes | LEGACY COMPAT — employer panels |
| `src/lib/supabaseStorage.ts` | bucket names + `{userId}/{filename}` path helper (no live calls found in this file) | LEGACY COMPAT — storage helper, currently unused by canonical flows |
| `src/lib/localAuth.ts` | localStorage privileged local-session fallback | LEGACY COMPAT — flagged for removal since Phase 2; superseded by canonical session |
| `src/hooks/useAuth.ts` | `supabase.auth.*` (getSession / onAuthStateChange / signInWithPassword / signUp) | LEGACY COMPAT — auth for the legacy product surfaces |
| `src/app/dashboard/page.tsx`, `src/app/dashboard/employer/page.tsx`, `src/app/interviews/page.tsx`, `src/app/interview/[id]/page.tsx`, `src/app/interview/[id]/analysis/page.tsx` | Supabase queries via the libs above | LEGACY COMPAT |

## Canonical API surface (already exists)

`src/lib/api/` (typed client + types) targets the canonical backend
(`/api/v1`, 192 routes). The canonical pages (`/jobseeker/*`,
`/company/*`, `/admin/*`, communications, talent) use it exclusively —
they have **zero** Supabase dependency.

## Findings

1. **Split-brain persists only in the legacy surfaces.** Careers
   (public), legacy dashboard/employer/interviews, and login/register use
   Supabase directly; everything canonical uses the typed API.
2. **Supabase Auth is the auth source for the legacy surfaces only.**
   It is never the source of truth for canonical RBAC/Work ID/membership/
   governance (verified throughout Phases 3–13).
3. **`localAuth.ts`** is a privileged local-session fallback — the
   highest-risk legacy auth artifact; removal is part of the login/register
   cutover.
4. **Storage helper** (`supabaseStorage.ts`) is inert today (no callers
   found in the audited paths) — safe to retire with the storage
   workstream.
5. **Careers reads are public data** (companies/offices/jobs) plus
   user-scoped `saved_jobs` behind RLS — the lowest-risk cutover target
   after canonical company/opportunity data exists.

## Cutover plan (frontend workstream, NOT executed in Phase 13)

Ordered by risk:

1. **Auth cutover**: login/register/`useAuth` → canonical `/api/v1/auth`
   (access+refresh); delete `localAuth.ts` fallback; session storage in
   the canonical session layer. This retires Supabase Auth for the app.
2. **Careers public read cutover**: `careers/api.ts` → typed API
   (opportunities/company catalogue) once the careers corpus is migrated.
3. **Employer panels cutover**: `employerApi.ts` → Company OS routes
   (job_postings, applications, offers), retiring direct `jobs` writes.
4. **Saved-jobs/notifications cutover**: `saved_jobs` →
   `opportunity_interactions`; notifications → `/api/v1` notifications.
5. **Storage cutover**: `supabaseStorage.ts` + legacy buckets → the
   provider-neutral document API (needs the document-storage workstream).
6. **Retire** `lib/supabase.ts` + `@supabase/supabase-js` dependency
   entirely once no surface imports it.

Compatibility guarantee for Phase 13: nothing above was changed; the live
Careers platform keeps working untouched.