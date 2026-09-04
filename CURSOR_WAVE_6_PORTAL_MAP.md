# CURSOR WAVE 6 — LOCAL PORTAL QA MAP

**Status:** Inspected on localhost 2026-09-05  
**Frontend:** http://localhost:3000  
**API:** http://127.0.0.1:8000 (isolated `backend/asktrabaajo_wave6.db`)  
**Hosted Supabase:** **UNTOUCHED**

Routes that do not exist as Next.js pages are marked MISSING. Do not invent them.

## A. Public / Auth

| Route | Exists | Guard | Visual | Functional (localhost) |
|---|---|---|---|---|
| `/login` | yes | public, now standalone (no marketing chrome) | VISUALLY VERIFIED vs Figma `9:73` | login, invalid credentials, MFA step, redirect |
| `/register` | yes | standalone | VISUALLY VERIFIED vs Figma `9:6` | validation, jobseeker/employer intent |
| `/forgot-password` | yes | standalone | VISUALLY VERIFIED (same auth shell) | posts `/auth/forgot-password` |
| `/` about/features/contact/leadership | yes | marketing Header+Footer | not Wave 6 Figma portals | public marketing pages in this app |
| Protected `/jobseeker` unauthenticated | yes | `PortalGuard` | client redirect to `/login?next=` | verified |

Canonical auth only (`AuthContext` + `/api/v1/auth/*`). `useAuth` / Supabase remain on legacy Careers only.

## B. Jobseeker / Candidate

| Requested | Actual route | Exists |
|---|---|---|
| `/jobseeker` dashboard | `/jobseeker` | yes |
| `/jobseeker/dashboard` | — | **MISSING** (alias not implemented; Home is `/jobseeker`) |
| `/id/work-id` | `/id/work-id` | yes |
| `/jobseeker/documents` | same | yes |
| `/jobseeker/credentials` | same | yes |
| `/jobseeker/work-dna` | same | yes |
| `/jobseeker/career` | same | yes (goals/milestones/advisor live here) |
| `/jobseeker/advisor` | — | **MISSING** as a route; Career Advisor is `/jobseeker/career` |
| `/jobseeker/goals` | — | **MISSING** as a route; on Career |
| `/jobseeker/milestones` | — | **MISSING** as a route; on Career |
| `/jobseeker/opportunities` + `[id]` | yes | yes |
| `/jobseeker/applications` | yes | yes |
| `/jobseeker/interviews` | yes | yes |
| `/jobseeker/ai-interview` | yes | yes |
| `/jobseeker/interview-prep` | yes | yes |
| `/jobseeker/offers` | yes | yes |
| `/jobseeker/messages` | `/jobseeker/communications` | yes (messages nav) |
| `/jobseeker/notifications` | yes | yes |
| `/jobseeker/privacy` | yes | yes |
| `/jobseeker/athena` | yes | yes |
| `/id` account/security | yes | yes |

All of the existing Candidate routes above were opened in Playwright at 1440×900. `/jobseeker` and `/jobseeker/athena` also at 390×844.

## C. Employer / Company

| Requested | Actual route | Exists |
|---|---|---|
| `/company` | yes | yes |
| `/company/profile` | yes | yes |
| `/company/members` | yes | yes |
| `/company/jobs` | yes | yes |
| `/company/jobs/[id]` | — | **MISSING** (list + `/jobs/new` only) |
| `/company/jobs/new` | yes | yes |
| `/company/jobs/[id]/edit` | — | **MISSING** |
| `/company/talent` | `/company/candidates` | yes |
| `/company/talent/[id]` | `/company/candidates/[id]` | yes |
| `/company/pipeline` | yes | yes |
| `/company/pipeline/[id]` | — | **MISSING** (detail is in-list / application APIs) |
| `/company/interviews` | yes | yes |
| `/company/ai-interviews` | `/employer/ai-interviews` | yes |
| `/company/offers` | yes | yes |
| `/company/messages` | `/company/communications` | yes |
| `/company/outreach` | — | **MISSING** as a page; outreach is inside Talent Graph |
| `/company/analytics` | yes | yes |
| `/company/notifications` | yes | yes |
| `/company/billing` | `/employer/billing` | yes |
| `/company/settings` | yes | yes |
| `/company/athena` | yes | yes |

Nav labels Workforce → members, Planning → profile (profile is the supported planning surface).

## D. Super Admin

Opened: `/admin`, `/admin/governance`, `/admin/governance/enforcement`, `/admin/governance/appeals`, `/admin/governance/audit`, `/admin/governance/teams`, `/admin/finance`, `/admin/support`, `/admin/operations`, `/admin/athena`, `/admin/notifications`, `/admin/settings`.

Case detail `/admin/governance/[id]` exists but was empty in DEV (no cases) — not opened with a real id.

Not invented: People, Companies, Governments, Marketing, user search.

## E. Athena

| Route | State on localhost | Visual |
|---|---|---|
| `/jobseeker/athena` | `AI_PROVIDER=none` → not configured, no composer, OS capability cards | VISUALLY VERIFIED |
| `/company/athena` | same degraded honesty | VISUALLY VERIFIED (opened) |
| `/admin/athena` | architecture-only / Soon | VISUALLY VERIFIED |

No fake replies.

## F. Work ID

`/id/work-id` opened. Empty/new identity: 0% completeness, profile editor, add-experience/education/employment/skill/credential, documents vault empty. `/jobseeker/privacy` and `/id` cover visibility/security.

## G. Government

**No `/government` route exists.** Figma file `IGQTJOpvt7odmdHjLazDDA` is design-only. Backend is aggregate-only (`workforce.aggregates.read`). Foundation / not implemented.

## H. Legacy (not Wave 6 portals)

`/careers/*`, `/dashboard/*`, `/interview*`, `/interviews` — left untouched.
