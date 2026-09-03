# PHASE 6 — COMPANY / HR / RECRUITER EMPLOYMENT OS

**Status:** Complete (foundation phase, functional proof)
**Scope:** The employer half of AskTrabaajo, built on the Phase 3 tenancy/RBAC foundation and the Phase 5 jobseeker Career OS — one platform, one data model, one application lifecycle.
**Non-goals honored:** No ATS clone. No parallel job universe. No AI interviewer, no facial/behavioural analysis, no lie detection, no payments, no blockchain, no government individual-data access. The legacy Careers platform is untouched.

---

## 1. Company architecture

The Company OS is a set of **organization-scoped services and routes** over the canonical model, not a separate product:

```
Company (Organization tenant, kind=employer|recruiter)
 ├── CompanyProfile (1:1 with Organization)
 ├── Members (User ↔ Organization, role-scoped RBAC)
 ├── JobPosting (company-owned lifecycle)
 │      └── publish ──► canonical Opportunity (ONE catalogue)
 ├── JobApplication (shared with the jobseeker; job_id link)
 │      └── state machine (one authoritative lifecycle)
 ├── ScreeningResponse / InterviewScorecard / Interview
 ├── Offer (created here, decided in the candidate's Offer Center)
 └── DocumentRequest (candidate-authorization gate into Work ID documents)
```

Every route lives under `/api/v1/company/{organization_id}/…`, every read/write is
tenant-scoped, and every action requires **membership + a specific permission**.

## 2. Organization model

Reused the Phase 3 `Organization` entity (kind, status, membership) unchanged. Phase 6 adds:

- **CompanyProfile** (1:1, lazy-created): legal_name, display_name, industry, sector, country, city, website, company_size, company_type (startup/sme/enterprise/…), description, contact, `verification_status` (default `unverified`).
- Self-service org creation remains: any user may create an employer/recruiter org and becomes its `org_admin`. Platform/government orgs are still super-admin-provisioned only.

## 3. Company roles

Roles come from the **catalog** (`app/models/catalog.py`) and are validated against org kind (`role_scope_allows_org_kind`). In an employer org:

- **org_admin** — full company scope (profile, jobs, applications, interviews, offers, analytics, members) + billing.read
- **hr** — jobs + pipeline + interviews + offers + analytics (no members.manage, no company.manage)
- **recruiter** — pipeline + interviews (view jobs, no publish, no offers, no analytics)
- **hiring_manager** — view + interviews (no decisions, no offers)

Platform scope (`super_admin` etc.) is never reachable from an employer membership — the Phase 1 vulnerability class is structurally impossible (platform roles exist only in platform-kind orgs, and `require_super_admin` checks platform memberships).

## 4. Permissions

New permission codes added to the catalog: `jobs.view`, `jobs.publish`, `candidates.view`, `applications.view`, `applications.manage`, `interviews.manage`, `offers.create`, `offers.manage`, `analytics.view`, `company.manage`. Enforcement is `require_org_permission(db, user, "<permission>", organization_id)` — resource-scoped, never a bare `role == "employer"` check.

## 5. Recruiter workflow

Recruiters operate the **pipeline**: list applications (filter by status/job), open the review, advance/hold/reject with an audited note, schedule and manage interviews, request candidate documents, and view analytics. The frontend proof (Pipeline page) exposes exactly this workspace; permission chips render the caller's actual grants.

## 6. Job lifecycle

`JobPosting` statuses are constants from the canonical enum set (draft → pending_review → published → paused/closed/archived). `create_job` / `update_job` / `publish_job` / `pause_job` / `close_job` in `app/services/company_os.py` are the only writers; the API never lets a handler set status directly. `update_job` whitelists editable fields and rejects unknown ones.

## 7. Opportunity integration — ONE universe

Publishing a job calls `_sync_opportunity`: it creates (or updates, idempotently) a single canonical `Opportunity` owned by the organization (`company_id`), marked `source="platform"`, `status="active"`, carrying the job's title/skills/location/salary/etc. Closing/pausing the job flips the opportunity. The jobseeker Career OS then discovers and applies to that same row — there is no second job universe.

## 8. Candidate discovery / matching

Phase 6 does **not** add a second matching engine. Jobseekers already discover published opportunities through the Phase 5 explainable matcher. The company side reads applications that arrived through that flow; discovery-by-search across candidate pools (public profiles only) is deliberately deferred (Phase 7) rather than bolted on half-built.

## 9. Candidate pipeline

`REVIEW_STATUSES` = applied/application_received/screening/assessment/interview/on_hold feed `needs_review`. Employer decisions (`advance`/`hold`/`reject`) run through the same `applications.decision` service used by the Phase 5 state machine — `JobApplication.status` is written only by the state machine, and every transition records an `ApplicationEvent`. Cross-tenant reads of another org's application return 404 (row hidden after membership is proven); non-members of the owning org get 403 before any row lookup.

## 10. Application lifecycle

One `job_applications` table, one state machine, two interfaces:
- jobseeker side (Phase 5): apply / withdraw
- employer side (Phase 6): screening → interview → offer advancement via `applications.manage`

A denormalized `job_id` FK (nullable, `ON DELETE SET NULL`) links an application to the company `JobPosting` when the opportunity is a published job — the pipeline joins through it or falls back to `opportunity.company_id`.

## 11. Work ID access — progressive disclosure

The review endpoint returns a **candidate snapshot**, not the Work ID dump: professional summary, skills, disclosure flags (which Work ID sections the candidate has shared for this application), and the audited event timeline. Whether the candidate has a **live consent grant** is surfaced (`has_live_consent`) so recruiters know what they may lawfully use. Full Work ID sections beyond the snapshot require the Phase 4 authorization model.

## 12. Document consent

`DocumentRequest` (company → candidate): application, document_type, purpose, status pending/approved/declined/expired. Approval happens on the **jobseeker** side (`/api/v1/jobseeker/document-requests/{id}/approve`), which creates a live organization grant through the Phase 4 document layer (`documents.service`) — so a company can never touch a document without the candidate's explicit authorization, and every access is audited. Employer route only creates requests; the candidate holds the keys.

## 13. Screening

`JobPosting.screening_questions` (structured, per job) and `ScreeningResponse` (candidate answers, auditable) exist as the foundation. The screening decision flows through the standard pipeline decision endpoint. No AI screening was implemented.

## 14. Interviews

`Interview` rows are created company-side (`interviews.create`) against an application with scheduled_at, duration, mode (video/phone/onsite), interviewer, meeting link, notes. Company endpoints list interviews, mark complete, and confirm reschedules; the candidate requests reschedules jobseeker-side (Phase 5 policy: limited reschedule count + reason). Rescheduling is a controlled, audited workflow in both directions.

## 15. Interview feedback

`InterviewScorecard`: criteria (role-relevant), strengths, concerns, recommendation (advance/hold/reject), notes. No personality scoring, no protected-characteristic collection, no behavioural inference. Module docstrings state this explicitly.

## 16. Hiring decisions

`POST /applications/{id}/decision` with `action ∈ {advance, hold, reject}` and an optional audited note. Every decision: validates state, transitions the shared state machine, records an `ApplicationEvent`, writes an audit entry (`application.decision.<action>`), and notifies the candidate. Non-live statuses are rejected by the machine.

## 17. Offers

Employer creates a **draft** offer (salary/currency, equity, benefits, start date, location, terms, expiry window) → `send` moves it to `sent`, where it appears in the candidate's Phase 5 Offer Center for explicit accept/decline; acceptance syncs back to the shared application state (`accepted`). Offers may be withdrawn. No legally binding documents are auto-generated — terms come from the company's authoritative input.

## 18. Notifications

Reused the Phase 5 `notifications` service. Decision transitions and interview scheduling notify the candidate (`application` / `interview` kinds). The candidate-facing unread badge on their dashboard reflects these. Company-side notification preferences were intentionally not built (Phase 7) to avoid notification spam before the preference model exists.

## 19. Analytics

`hiring_analytics` (org-scoped, `analytics.view`): open/total jobs, applications total and by status, needs_review, interviews scheduled, offers pending, and conversion ratios (screening→interview→offer). No candidate protected characteristics are ever collected or aggregated.

## 20. Careers integration — the controlled adapter

`backend/scripts/careers_ingest.py` is the **only** sanctioned path from the legacy Careers corpus into the canonical model:

```
careers SQL corpus ──parse──► normalize ──validate──► dedupe ──provenance──►
JobPosting (draft) ──publish──► Opportunity (source="careers_compat") ──► jobseeker discovery
```

- **Parser:** reads the real `INSERT INTO public.jobs (…) SELECT …` dollar-quoted format; anchors deterministically on the slug token, tolerant to subquery-wrapped value expressions; malformed rows are counted and skipped — never half-written.
- **Provenance:** each row carries `imported_from="careers:<company>:<slug>"`; published opportunities are re-marked `source="careers_compat"` (never presented as native postings). Import target defaults to a deterministic placeholder org or `--organization-id` for a real tenant.
- **Idempotent:** re-running skips existing slugs.
- **Validated:** 104/104 corpus jobs parse; end-to-end import tested on a scratch DB (create → re-run → 0 created / N existing); three adapter regression tests exercise the parser against the **real corpus file** so format drift fails loudly.
- **No destruction:** the corpus SQL, legacy careers frontend, and Supabase careers tables are untouched.

## 21. API endpoints added

All under `/api/v1/company/{organization_id}` (25 company endpoints; canonical surface now 119 routes):

| Group | Endpoints |
|---|---|
| Profile | GET/PATCH `/profile` |
| Dashboard | GET `/dashboard` |
| Jobs | GET list/`{id}`, POST create, PATCH `{id}`, POST `{id}/publish|pause|close` |
| Applications | GET list, GET `{id}` review, POST `{id}/decision` |
| Interviews | POST create, GET list, POST `{id}/complete`, POST `{id}/confirm-reschedule`, POST `{id}/scorecards` |
| Offers | POST create, GET list, POST `{id}/send`, POST `{id}/withdraw` |
| Documents | POST `document-requests`, GET `document-requests` |
| Analytics | GET `/analytics` |

Jobseeker-side additions: GET `/jobseeker/document-requests`, POST `…/{id}/approve`, POST `…/{id}/decline` (the candidate gate for company document requests).

## 22. Frontend (proof)

- `/company` — org picker + self-service org creation + employer dashboard (open jobs, applications, needs review, interviews today/upcoming, offers pending/accepted, recent applications, permission chips).
- `/company/jobs` — job list, create-draft form, publish/pause/close, live catalogue indicator.
- `/company/pipeline` — application list with status filter, per-candidate review (snapshot, disclosure flags, timeline), decisions with notes, interview scheduling, document requests, offer create/send.

All through the single typed API client; types added to `frontend/src/lib/api/types.ts`. Functional proof UI, not the Figma design.

## 23. Database changes

- **Migration `0004_company_employment_os`** (additive, reversible): `company_profiles`, `job_postings`, `screening_responses`, `interview_scorecards`, `document_requests`; catalog seeding for the new permissions/roles (upgrade → 38 tables). Validated locally: upgrade → downgrade → re-upgrade, including on SQLite.
- **`job_applications.job_id`** denormalized employer link (nullable FK, `ON DELETE SET NULL`, indexed).
- **Enums:** job statuses, offer draft/sent lifecycle, interview modes, org verification, document-request statuses, scorecard recommendations, hiring org kinds.
- **Applied migrations:** none to any shared/production database. All testing ran on isolated in-memory SQLite; the production-refusal guard still holds.

## 24. Security model

Membership + permission + tenant-scoped rows everywhere; 403 for non-members before any lookup; 404 to hide other tenants' rows; super-admin platform scope unreachable from employer memberships; candidate documents require candidate-approved grants; audit events on every decision, offer, interview, document request, and profile change; no secrets introduced; structured logs never carry payloads.

## 25. Tenant isolation (test-proven)

`test_company_phase6.py` proves: Company A cannot read/publish/mutate Company B jobs, applications, interviews, or offers; a non-member of the owning org gets 403; cross-tenant hidden rows resolve to 404; role boundaries hold (recruiter cannot publish jobs or create offers without the permission); offer acceptance synchronizes the shared application state; document requests never auto-grant access.

## 26. Testing

Canonical suite now **94 passing** (81 prior + 10 company + 3 careers-ingestion). Coverage: tenant isolation, membership RBAC, job ownership/lifecycle/publish, pipeline decisions and state transitions, interview scheduling/confirmation, offer create→send→candidate accept, document-request consent flow, candidate privacy at review, careers-adapter parsing + idempotent provenance-marked import.

## 27. Known limitations

- No company-side **candidate search/discovery** yet (Phase 7) — discovery flows through jobseekers finding published jobs.
- `ScreeningResponse` and interview **scorecard UI** exist as model/API only; no scorecard frontend page (behind pipeline `interviews` endpoints).
- Interview **meeting links** are manual strings; no calendar/video provider integration.
- No job-quality/bias-assist AI (deliberate).
- Offer **documents** are not yet uploaded/attached (only structured terms).
- Company notification preferences not built; company-side email sending not wired (no SMTP provider decision).
- Adapter skill extraction is a bounded keyword list — acceptable for a provenance-marked demo import; the real employer pipeline (native job creation) is the high-quality source.

## 28. Production readiness

**READY (foundation):** tenant isolation model + tests, RBAC catalog, one-lifecycle state machine, additive migrations, adapter with provenance, offer↔application sync, document-request consent gate.
**NOT READY:** Postgres-specific behaviors (unique handling, RLS) untested — migrations were validated on SQLite; real-volume indexing; seed/ingestion into a live Postgres; company frontend beyond proof pages; email/SMTP; analytics against live data.
**UNKNOWN:** Postgres RLS posture once Supabase hosts the canonical schema; real-world recruitment scale.

## 29. Phase 7 dependencies

1. **Candidate discovery/search** (company side) building on public-profile visibility controls (Phase 4) — needs the visibility-model extension decision.
2. **Employer-side screening UI + scorecard flows** on top of existing models.
3. **Company notifications/preferences + email delivery** — needs SMTP/email vendor approval.
4. **Careers ingestion into a live environment** — needs the Phase 7 ingestion decision (one-time compat import vs. adapter tooling per environment).
5. **Matching parity/explainability surfacing** inside the company pipeline (the engine already exists).
6. Super Admin (Phase 8+) needs the audit trail this phase already writes for every company action.

## 30. Decisions requiring approval

- **(a)** Approve Phase 6 and proceed to the agreed Phase 7 sequence.
- **(b)** Careers-data ingestion target for a shared environment: run the adapter as a one-time compat import (recommended, provenance-marked, idempotent) vs. deferring ingestion until the legacy careers backend retires.
- **(c)** Whether candidate discovery/search should be Phase 7's first slice (it depends on extending the Phase 4 visibility model for company-facing discovery).
- **(d)** Open items carried from earlier phases: the Phase 1 hygiene batch remains uncommitted (23 modified + ~40 untracked files, deliberately untouched — requires owner approval), and external credential rotation remains open.
