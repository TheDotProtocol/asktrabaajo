# CURSOR WAVE 3 CLOSURE — Employer / Company Employment OS

**Status:** IMPLEMENTED (local, unpushed)  
**Depends on:** Wave 2 ACCEPTED  
**Figma:** [AskTrabaajo — HR](https://www.figma.com/design/TWxgrQJPdyGSsbTkM8gX1b/AskTrabaajo---HR) (`TWxgrQJPdyGSsbTkM8gX1b`)  
**Hosted database:** **UNTOUCHED**

Wave 3 turns the Employer/Company portal into a real client of `/api/v1` inside the HR Figma shell. Wave 1 auth/RBAC/OrgProvider and Wave 2 Candidate OS were not replaced.

---

## 1. What was implemented

- `EmployerShell` — 240px sidebar, org switcher, unread badge, gold/black brand matching Candidate OS
- Command center dashboard from `GET /company/{org}/dashboard`
- Company profile + honest offices/departments (profile city/country + job.department values)
- Members / RBAC (`/organizations/{id}/members`)
- Job list, multi-step draft creation, publish/pause/close, clone-as-template
- Talent Graph + candidate profile (existing APIs, restyled)
- Pipeline + document requests + outreach (existing)
- Interviews list + complete / confirm-reschedule
- Offers list + send / withdraw
- AI Interviews + human decision (existing employer page)
- Communications, analytics, notifications, billing, settings
- Athena HR entry is honest (Wave 4)

## 2. HR Figma screens mapped

| Frame | Route | API / note |
|---|---|---|
| employer-command-center | `/company` | `/company/{org}/dashboard` |
| athena-hr-command | `/company/athena` | Honest entry — no fake chat |
| workforce-intelligence / employee-directory | `/company/members` | `/organizations/{id}/members` |
| workforce-planning / employer-brand / company-work-id | `/company/profile` | `/company/{org}/profile` |
| job-creation | `/company/jobs/new` | `POST /company/{org}/jobs` (draft) |
| Jobs nav | `/company/jobs` | jobs + publish/pause/close |
| talent-pool / candidate-search / talent-intelligence | `/company/candidates` | `/talent/{org}/candidates/*`, pools |
| candidate-profile | `/company/candidates/[id]` | public/disclosure only |
| recruitment-pipeline | `/company/pipeline` | applications + decisions |
| interview-center / scheduling | `/company/interviews` | `/company/{org}/interviews` |
| interview-results / ai-interviewer-config | `/employer/ai-interviews` | `/ai-interviews/*` + human decision |
| offer-center | `/company/offers` | `/company/{org}/offers` |
| hr-analytics | `/company/analytics` | `/company/{org}/analytics` |
| notifications | `/company/notifications` | user-scoped `/jobseeker/notifications` |
| settings / security-center | `/company/settings`, `/id` | members, billing, auth |
| onboarding, performance, learning, compensation-intelligence, KYC viewer | — | **No first-class API** — not fabricated |

## 3. APIs connected

All through `frontend/src/lib/api/`. No mock APIs. No second matcher.

## 4. Backend changes

**None.** Existing company/talent/billing/AI interview routes were sufficient. Gaps documented instead of inventing offices/templates/mission tables.

## 5–7. Database

- No Alembic changes
- Development DB **not rebuilt** on hosted PostgreSQL
- Isolated sqlite e2e only
- See `CURSOR_WAVE_3_DB_CLASSIFICATION.md`

## 8–9. Security tests

`scripts/wave3_employer_e2e.py`:

- DEV_ORG_A vs DEV_ORG_B
- A cannot read/modify B jobs, applications, interviews, offers, pools, communications, billing
- Expected **403/404**, not empty 200
- Candidate dashboard still works (Wave 2 regression)

Canonical `tests_phase3`: **250 passed / 11 skipped / 0 failed** (sqlite).  
PostgreSQL RLS on local scratch `p14_test`: **11/11 passed**.  
Frontend: `tsc --noEmit` PASS · `npm run lint` PASS (0 errors; 5 pre-existing Careers warnings) · `npm run build` PASS.  
Wave 2 candidate E2E: **PASS** (regression).

## 10. What remains

- Athena HR chat (Wave 4)
- First-class offices/departments/job-template catalogs (no canonical tables)
- Figma workforce/performance/learning/onboarding product surfaces
- Hosted schema reconciliation (operator)
- Public website CTAs

## 11. Genuinely blocked

- Real AI / payments / voice-video providers
- Production deploy / push
- Government / Super Admin Figma

## 12. Ready for Wave 4

Yes — Athena product UI + confirmation gates, on the Wave 1–3 foundation.

Do not start Wave 4 until a separate approval prompt.
