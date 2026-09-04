# PHASE 12 — SUPABASE RECONCILIATION

Status: **READ-ONLY / ARTIFACT-BASED.** The live Supabase project
(`zrvrjqwboylvvzusorry`) was **NOT connected, NOT inspected via live
credentials, and NOT modified.** Everything below is derived from the
version-controlled artifacts in this repository (SQL schema files, seed
scripts, session notes, phase reports) and the canonical implementation
on disk. See PHASE_12_REPORT.md for the hard-stop conditions that led to
this posture.

---

## A. Legacy architecture overview

The historical AskTrabaajo (the "MVP", pre-Phase-3) is a two-part system:

1. **Next.js frontend** reading/writing **Supabase directly** (client SDK,
   Supabase Auth, RLS) for careers, dashboard, employer panels,
   interviews, documents.
2. **FastAPI backend** (legacy `backend/main.py` + `backend/api/*`) with an
   Integer-ID ORM that never matched the Supabase UUID schema — "split
   brain" (see AUDIT_REPORT.md). 107 legacy routes remain importable.

Repository artifacts describing the legacy database:

| Artifact | Contents |
|---|---|
| `supabase-schema.sql` | Core schema: `profiles`, `jobs`, `applications`, `interviews`, `test_results`, `payments`, `notifications`, `documents` + auth trigger + RLS + update triggers |
| `supabase-careers-schema.sql` | Careers: `companies`, `offices`, `department_catalog`, `company_departments`, `company_media`, `saved_jobs`, `application_stages`, `candidate_resumes`, `candidate_certificates`, `company_admins`, `job_templates`, `talent_pool` + jobs extension columns + RLS |
| `supabase-careers-ext.sql` | `job_offers` + `is_super_admin()` + super-admin write policies |
| `supabase-storage.sql` | Storage buckets `user-documents`, `kyc-documents`, `kyc-selfies` + object policies |
| `scripts/seed-careers-platform.sql` | 294 INSERTs — portfolio companies, departments, offices, jobs (marketing corpus) |
| `scripts/master-portfolio-jobs*.sql` | 104 INSERTs — jobs corpus |
| `scripts/*.sql` (rest) | Update/restructure scripts against the careers corpus |
| `sessions.md` | Session notes describing sample/demo data (3 sample jobs, test users) |
| `supabase-vercel-setup.md`, `DEPLOYMENT_GUIDE.md`, `railway-setup.md` | Deployment notes (now sanitized of secrets) |

## B. Current canonical architecture overview

FastAPI modular monolith (`backend/app/`) with a canonical UUID identity
model, org/membership RBAC, Work ID spine, company OS, talent graph,
outreach/communications, governance, enforcement, appeals, audit/events,
rate limiting, and a notification abstraction. Schema is owned **only** by
Alembic migrations `0001`–`0009` (head `0009`, 63 tables). 192 `/api/v1`
routes; 153 canonical tests green; legacy backend untouched at 107 routes.
PostgreSQL (Supabase-hosted) is the intended database; SQLite is
development/test only and rejected by config in staging/production.

## C. Table-by-table mapping

| Legacy Object | Current Canonical Object | Action | Data Migration Required? | Reason |
|---|---|---|---|---|
| `profiles` | `users` + `person_profiles` (+ `memberships`, `organizations`) | TRANSFORM | Yes, per-field (see §F, §6) | One table mixed identity, profile, contact, career data, roles, government fields, admin flags. Canonical splits identity/RBAC/profile/privacy. |
| `jobs` | `job_postings` + `opportunities` + `opportunity_requirements` | TRANSFORM | Yes | Employer-published jobs become company `job_postings`; structured requirements move to `opportunity_requirements`; discoverable listings map to `opportunities`. |
| `applications` | `job_applications` + `application_events` | REPLACE | Yes | Lifecycle is event-driven in canonical; `status` + `pipeline_stage`/`tracker_data` are derived from events, not stored redundantly. |
| `application_stages` | `application_events` | REPLACE | Yes | Stage history = ordered events on the application. |
| `interviews` | `interviews` (canonical) | REPLACE | Yes | Canonical interviews attach to a `job_application` (not loose job+applicant+employer triples), carry candidate reschedule policy and scorecards. |
| `test_results` | — (none) | DEPRECATE | No | AI assessments were never part of the canonical employment journey; deprecated, not recreated. |
| `payments` | — (none; payments explicitly deferred) | DEPRECATE | No | Phase boundary: payments belong to a later commerce phase. Preserve nothing; do not recreate. |
| `notifications` | `user_notifications` | REPLACE | Yes (optional) | Same concept, canonical UUID/tenant shape; in-app + provider-neutral channel abstraction (Phase 9). |
| `documents` | `person_documents` + `document_access_grants` + `consents` + `credential_states` | TRANSFORM | Yes (metadata only; files via storage §F) | Candidate-controlled, consent-gated, auditable. Old single table has no verification/disclosure state. |
| `candidate_resumes` | `credentials` + `person_documents` | TRANSFORM | Yes (metadata) | Resume content becomes a credential/document with verification state rather than a bespoke JSON blob table. |
| `candidate_certificates` | `credentials` | TRANSFORM | Yes | Direct map: certificate → credential (title/issuer/date/URL + verification state). |
| `companies` | `organizations` + `company_profiles` | TRANSFORM | Yes | Tenant org vs. marketing portfolio company are different concepts; portfolio/public companies map to `company_profiles` with `organization_id` where a tenant exists. |
| `offices` | `company_profiles` offices relation (Company OS) | TRANSFORM | Yes | Global hiring-centre corpus maps into the company OS office model. |
| `department_catalog` | Company OS department catalog | TRANSFORM | Yes | Reference catalog maps directly. |
| `company_departments` | Company OS company↔department link | TRANSFORM | Yes | Direct map. |
| `company_media` | Company OS media model | TRANSFORM | Yes | Direct map (public marketing media only). |
| `saved_jobs` | `opportunity_interactions` (talent graph) | REPLACE | Yes | Saved jobs = interaction on an opportunity; canonical already models this. |
| `company_admins` | `memberships` + RBAC `roles`/`role_permissions` | TRANSFORM | Yes | `admin_role` → canonical role codes (recruiter / hiring_manager / company admin). Never a flat flag. |
| `job_templates` | — (none) | DEPRECATE | No | Template concept not in canonical scope; structured requirements supersede. Preserve nothing. |
| `talent_pool` | `talent_pools` + `talent_pool_members` | REPLACE | Yes | Phase 7 canonical model (org-scoped, saved candidates, provenance). |
| `job_offers` | `offers` (company OS) | REPLACE | Yes | Canonical offer attaches to application/opportunity; acceptance transitions into onboarding. |
| `profiles.is_super_admin` | RBAC platform roles (`governance`/`enforcement` roles + permissions) | REPLACE | Yes (mapping) | See §J. Never a hidden universal bypass. |
| `handle_new_user()` trigger | App-created identities (auth service) | REPLACE | No | Canonical identity is created by the backend, not a DB trigger on `auth.users`. |
| `update_updated_at_column()` trigger | ORM `onupdate` timestamps | REPLACE | No | Moved into the application layer. |
| `is_super_admin()` function | RBAC permission checks in `authz` service | REPLACE | No | Function removed with Supabase Auth dependency. |
| Storage `user-documents` bucket | Provider-neutral document storage abstraction + `person_documents` | TRANSFORM | Yes (files) | Files must be re-uploaded/migrated under canonical consent/audit rules — NOT copied via old RLS. |
| Storage `kyc-documents` bucket | `credentials` (KYC) + restricted storage | TRANSFORM | Yes (files, guarded) | Highest-sensitivity class; migration needs explicit consent + policy review. |
| Storage `kyc-selfies` bucket | — (none) | DEPRECATE | No | No facial/selfie capture exists in canonical architecture; deprecate for privacy reasons. |

## D. Legacy Auth mapping

| Legacy | Canonical | Action |
|---|---|---|
| Supabase Auth (email/password) via `@supabase/supabase-js` in the frontend | Application-owned JWT auth (`/api/v1/auth`, bcrypt, access+refresh tokens) | MIGRATE (temporarily RETAIN as compatibility path for the careers frontend until cutover; see §L) |
| `auth.uid()` as authorization root | Authenticated actor from the canonical session; RBAC permissions | REPLACE |
| `profiles.id = auth.users.id` coupling | Independent canonical `users` UUIDs created by the app | TRANSFORM |
| `handle_new_user()` trigger creating `profiles` | App registration/onboarding creates user + person profile + membership | REPLACE |
| Client-side Supabase sessions in `useAuth.ts` | Server-issued JWT stored by the app session layer | REPLACE |
| Frontend `lib/supabase.ts`, `lib/careers/supabase.ts` direct reads | Typed API client against `/api/v1` | MIGRATE (careers read path cutover is a frontend workstream, out of Phase 12 scope) |

**Separation principle:** authentication (who you are) and application
authorization (what you may do) are decoupled. Supabase Auth may remain as
a temporary authentication infrastructure for the legacy careers path, but
it is never the source of truth for RBAC, Work ID, membership, or
governance permissions.

## E. Legacy RLS mapping

| Legacy Policy | Current Equivalent | Gap | Required Action |
|---|---|---|---|
| `profiles` own-row select/update/insert (`auth.uid() = id`) | App-level authz + `person_profiles`/`users` owner checks; RLS `PERSON_TENANT_TABLES` plan (Phase 9 artifact) | RLS not yet enabled on shared DB; session-marker mechanism not deployed | Stage RLS behind a non-owner app role (§ Phase 12 infra doc); never `auth.uid()` |
| `jobs` public-read active / employer manage | `job_postings` org-scope app authz; `ORG_TENANT_TABLES` plan | Same as above | Same |
| `applications` applicant-or-employer select, applicant insert | `job_applications` person-scope + org access via related job | Same | Same |
| `interviews` applicant/employer | canonical `interviews` via application | Same | Same |
| `test_results` / `payments` own-row | deprecated (no canonical table) | n/a | n/a |
| `notifications` own-row | `user_notifications` person-scope | Same | Same |
| `documents` own-row | `person_documents` + grants + consents | Same | Same |
| `saved_jobs` own-row | `opportunity_interactions` person-scope | Same | Same |
| `candidate_resumes`/`candidate_certificates` own-row | `credentials` person-scope | Same | Same |
| `company_admins` super-admin-or-self | canonical membership RBAC | Same | Same |
| `job_templates` / `talent_pool` / `application_stages` super-admin-only | replaced by RBAC roles (`talent`, `governance`) | Same | Same |
| `companies`/`offices`/`departments` public read | public/company-profile read authz | Same | Same |
| Storage object policies (`auth.uid()::text = foldername[1]`) | Provider-neutral storage; access via signed URLs + `document_access_grants` | Old policies assume Supabase Storage + auth.uid(); canonical is provider-neutral | Define storage abstraction policies in staging; do not copy old object policies |

**Target RLS design:** database-level RLS is defense-in-depth only, keyed
to the canonical session identity (`app.current_user_id` /
`app.current_org_ids` set per transaction by the app, never client-
supplied). A non-owner `asktrabaajo_app` role is required; the Phase 9
`backend/app/db/rls.py` artifact is the reviewed starting point. Nothing
was enabled on any shared database.

## F. Legacy Storage mapping

| Legacy | Canonical | Action |
|---|---|---|
| `user-documents` (private, user-foldered) | Provider-neutral object storage; `person_documents` metadata + access grants + audit | TRANSFORM — files re-ingested under consent; old RLS dropped |
| `kyc-documents` (private, user-foldered) | `credentials` KYC class + restricted storage, admin review via governance workflow | TRANSFORM — guarded, consent-required |
| `kyc-selfies` (private) | none | DEPRECATE — no facial capture in canonical architecture |
| Storage object policies keyed on `auth.uid()` | Signed/controlled access keys, no raw public URLs, service-role access tightly scoped | REPLACE |

## G. Legacy Companies/Jobs/Application mapping

Covered in §C. Key decisions:

- **Companies:** portfolio/public companies (marketing corpus) → canonical
  `company_profiles`; tenant organizations (authored by users) →
  `organizations`. The careers corpus is valuable marketing content and
  should be migrated as reference content.
- **Jobs:** employer jobs → `job_postings` + `opportunities` +
  `opportunity_requirements`. Rich careers fields (`role_summary`,
  `responsibilities`, `preferred_qualifications`, `interview_process`,
  `job_benefits`, `work_mode`, `visa_sponsorship`, …) map to structured
  canonical fields where they exist or JSON metadata where they do not —
  never to redundant columns.
- **Applications:** `status` + `pipeline_stage` + `tracker_data` →
  derived state over `application_events`.

## H. Legacy Offers mapping

`job_offers` → canonical `offers` (company OS, Phase 6): offer attaches to
a `job_application` and an `opportunity`; acceptance transitions the
application state. Legacy fields (`salary_amount`, `currency`,
`start_date`, `offer_letter`, `expires_at`) map onto canonical offer
fields. No second offer system.

## I. Legacy Documents/KYC mapping

See §C/§F. Canonical target: candidate-controlled documents, credential
verification states (verified/unverified/pending/expired/revoked),
consent-controlled disclosure, auditable access grants, least privilege.
Administrators never casually browse user documents; KYC is
governance-gated.

## J. Legacy Admin/Super Admin mapping

`profiles.is_super_admin` + `is_super_admin()` + `auth.uid()` policies are
**replaced** by the canonical RBAC registry: platform roles
(`governance_moderator`, `governance_auditor`, `enforcement_manager`,
`super_admin`), granular permissions (`reports.*`, `enforcement.*`,
`appeals.*`, `governance.*`, `platform.audit.read`, …), organization
memberships, least privilege, full audit + enforcement + appeals. There is
**no** universal `admin.can_do_everything` shortcut. Functionality is
preserved; implementation is not.

## K. Deprecated objects

`test_results`, `payments`, `job_templates`, `kyc-selfies` bucket,
`handle_new_user()` trigger, `update_updated_at_column()` trigger,
`is_super_admin()` function, all `auth.uid()`-keyed policies once the
legacy frontend cutover completes.

## L. Unknown objects requiring later investigation

- **Live database contents of project `zrvrjqwboylvvzusorry`** — cannot be
  verified from the repository. Counts, actual rows, stray tables,
  production value: **UNKNOWN** (no approved live inspection).
- **Supabase Auth user records** — number of real users, password-hash
  compatibility for a forced-reset vs hash-copy decision: **UNKNOWN**
  (requires an approved read-only spike).
- **Storage object counts** — actual files in the three buckets: **UNKNOWN**.
- **Old Edge Functions / Supabase Functions** — none found in the repo;
  any deployed functions are unknown.
- Any tables/objects created ad hoc in the live project that are not in
  the four SQL artifacts: **UNKNOWN** (schema drift cannot be assessed
  without read access).

## M. Data migration risks

1. **No live inspection** — the migration plan is built on artifacts; a
   read-only schema diff against the live project is a mandatory first
   step of any future data migration.
2. **Identity mismatch** — legacy `profiles.id` is an `auth.users.id`;
   canonical users have independent UUIDs. A mapping table is required,
   plus a decision on preserving old UUIDs vs new.
3. **Credential migration** — legacy password hashes (Supabase Auth) may
   or may not be reusable; worst case is a forced reset (documented
   UNKNOWN until the auth spike).
4. **Document/KYC files** — re-upload/export under consent; never
   bulk-copy via old RLS. KYC has the highest sensitivity.
5. **Careers corpus is marketing content** — valuable but not
   user-generated data; migration priority is low and failure-tolerant.
6. **Bidirectional link risk** — canonical `job_applications` must be
   re-linked to canonical `opportunities`/`job_postings`; naive ID copying
   will break FKs.

## N. Security risks

1. Known-exposed credentials (Supabase anon/service-role, DB password,
   SMTP, OpenAI) from Phase 1 remain **unrotated** — a blocker for any
   live staging connection; rotation is an owner action.
2. `auth.uid()`-keyed RLS must never be copied; canonical app
   authorization + session-marker RLS is the target.
3. `profiles` combines sensitive fields (`government_id`, `tax_id`,
   `business_license`) — the split into least-privilege canonical domains
   is itself a security improvement; do not collapse it back.
4. Service-role key grants full DB bypass — must be removed from frontend
   reach and rotated; canonical backend never uses it.
5. Old storage policies would allow user-scoped but un-audited document
   access — canonical grants must be audited.

## O. Compatibility risks

1. **Careers frontend reads Supabase directly** — cutting it over to the
   API is a frontend workstream; doing it inside Phase 12 would expand
   scope and risk the live careers path.
2. **Legacy FastAPI backend (107 routes)** stays live during strangler
   migration; it does not share the canonical schema and must not be
   pointed at canonical tables.
3. **`supabase-schema.sql`/careers/ext share table names** with nothing in
   canonical migrations (verified in Phases 3–11) — no collision.
4. **RLS enablement requires an app role + session marker** — enabling
   policies without the deployment mechanism would lock the app out;
   staged enablement is mandatory.

## P. Recommended migration order

Phase 12 is documentation-only. When a future data-migration phase is
approved, the recommended order is:

1. **Read-only live schema diff** against the four artifacts (needs
   approved read credentials; identify drift + real row counts).
2. **Credentials rotation + staging Supabase project** (needs owner
   action; production keys must be rotated before any live work).
3. **Careers corpus migration** (lowest risk): companies → company
   profiles, offices, departments, jobs → postings/opportunities.
4. **Identity + auth migration** (highest value): users →
   `users`/`person_profiles`, membership/RBAC mapping, password strategy
   decision.
5. **Employment journey migration**: applications → events,
   interviews, offers.
6. **Documents/KYC migration**: metadata first, then consented file
   re-ingest under the canonical storage abstraction.
7. **Notification history** (optional): user_notifications backfill.
8. **Deprecation cutover**: freeze old schema writes; flip careers
   frontend to the API; only then retire Supabase Auth/Storage paths.

**Phase 12 conclusion — schema/reference migration is recommended; bulk
data migration is not currently justified from artifact evidence alone
(the repository contains only schema + marketing/seed corpus; real user
data presence in the live project is UNKNOWN).** No data migration was
executed.