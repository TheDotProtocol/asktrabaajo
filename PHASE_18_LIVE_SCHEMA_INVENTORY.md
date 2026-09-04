# Phase 18 — Live Schema Inventory

Read-only metadata inventory of the live Supabase database (project `zrvrjqwboylvvzusorry`, session pooler, PostgreSQL 17.6, database `postgres`, schema `public`, timezone UTC). No row contents are reproduced. No writes were performed.

## Schema inventory

- **Schemas present:** `auth`, `nextensions`, `graphql`, `graphql_public`, `public`, `realtime`, `storage`, `vault`.
- **Public tables: 21** (all legacy), **views: 0**, **sequences: 0**, **enum types: 0**.
- **Extensions:** `pg_stat_statements`, `pgcrypto`, `plpgsql`, `supabase_vault`, `uuid-ossp`.

## Row counts

| Table | Rows | Table | Rows |
|---|---|---|---|
| `application_stages` | 0 | `job_offers` | 0 |
| `applications` | 0 | `job_templates` | 0 |
| `candidate_certificates` | 0 | `jobs` | **222** |
| `candidate_resumes` | 0 | `notifications` | 0 |
| `companies` | **117** | `offices` | **10** |
| `company_admins` | 0 | `payments` | 0 |
| `company_departments` | **4,896** | `profiles` | **1** |
| `company_media` | 0 | `saved_jobs` | 0 |
| `department_catalog` | **48** | `talent_pool` | 0 |
| `documents` | 0 | `test_results` | 0 |
| `interviews` | **0** | | |

RLS is enabled on **all 21** tables (36 policies total). The table below records policy names per table; the policies themselves were not reproduced here.

## Per-table detail (columns, PK, FKs, constraints, indexes, RLS)

Legend: `pk=` primary key; `fk=` outgoing foreign keys; `uq=` unique constraints; `ix=` indexes.

### application_stages — 0 rows
- Columns: `id:uuid`, `application_id:uuid`, `stage:text`, `notes:text`, `created_at:timestamptz`
- pk=`id`; fk=`application_stages_application_id_fkey`; ix=—
- RLS policy: Super admins manage application stages

### applications — 0 rows
- Columns: `id:uuid`, `job_id:uuid`, `applicant_id:uuid`, `status:text`, `cover_letter:text`, `resume_url:text`, `applied_at:timestamptz`, `updated_at:timestamptz`, `pipeline_stage:text`, `tracker_data:jsonb`
- pk=`id`; fk=→`jobs`,→`profiles`; uq=`applications_job_id_applicant_id_key`
- RLS policies: Super admins read all applications; Super admins update applications; Users can create applications; Users can view own applications

### candidate_certificates — 0 rows
- `id`, `user_id`, `title`, `issuer`, `issued_at:date`, `credential_url`, `created_at`
- RLS policy: Users manage own certificates

### candidate_resumes — 0 rows
- `id`, `user_id`, `title`, `content:jsonb`, `file_url`, `ai_review:jsonb`, `is_primary:boolean`, `updated_at`, `created_at`
- RLS policy: Users manage own resumes

### companies — 117 rows
- `id`, `parent_id:uuid` (self-FK), `slug` (unique), `name`, `tagline`, `mission`, `vision`, `culture`, `culture_values:jsonb`, `benefits:jsonb`, `hiring_process:jsonb`, `life_at_company`, `logo_url`, `cover_image_url`, `website_url`, `industry`, `employee_count_range`, `is_portfolio`, `is_external`, `is_active`, `display_order`, `metadata:jsonb`, timestamps
- RLS policy: Public read active companies

### company_admins — 0 rows
- `id`, `user_id`, `company_id`, `admin_role`, `created_at`; uq on (user,company,role)
- RLS policies: Super admins manage/read company admins

### company_departments — 4,896 rows (junction)
- `company_id`, `department_id`, `is_hiring`; pk=(company,department)
- RLS policies: Public read company departments; Super admins manage company departments

### company_media — 0 rows
- `id`, `company_id`, `media_type`, `url`, `title`, `caption`, `display_order`, `created_at`
- RLS policies: Public read; Super admins manage

### department_catalog — 48 rows
- `id`, `slug` (unique), `name`, `category`, `display_order`
- RLS policy: Public read departments

### documents — 0 rows
- `id`, `user_id`, `filename`, `file_url`, `file_type`, `file_size`, `document_type`, `created_at`
- RLS policies: Users can manage own documents; Users can view own documents

### interviews — 0 rows ⚠️ THE SINGLE COLLISION
- Columns: `id:uuid`, `job_id:uuid`, `applicant_id:uuid`, `employer_id:uuid`, `scheduled_at:timestamptz`, `duration_minutes:integer`, `interview_type:text`, `status:text`, `meeting_link:text`, `notes:text`, `feedback:jsonb`, `created_at:timestamptz`, `updated_at:timestamptz`
- pk=`id`; fk=→`jobs`(job_id), →`profiles`(applicant_id), →`profiles`(employer_id); ix=`idx_interviews_applicant`
- **Incoming references:** 0 (no table has an FK pointing at `interviews`)
- RLS policies: Employers can manage interviews; Users can view own interviews
- Trigger: `update_interviews_updated_at`
- Domain: legacy interview *scheduling* records for the retired legacy video/facial-analysis prototype. Structurally unrelated to canonical `interviews` (created by migration 0003 under canonical tenancy/RLS model). **Empty** — no data-loss exposure.

### job_offers — 0 rows
- `id`, `application_id`, `company_id`, `candidate_id`, `job_id`, `salary_amount:numeric`, `currency`, `start_date:date`, `status`, `offer_letter`, `expires_at`, timestamps
- RLS policies: Candidates read own offers; Super admins manage offers

### job_templates — 0 rows
- `id`, `company_id`, `department_id`, `title`, `template_data:jsonb`, `created_by`, timestamps
- RLS policy: Super admins manage job templates

### jobs — 222 rows
- `id`, `employer_id`, `title`, `description`, `requirements:ARRAY`, `skills_required:ARRAY`, `location`, `remote_allowed`, `salary_min/max:integer`, `currency`, `employment_type`, `experience_level`, `status`, `application_deadline`, `company_id`, `office_id`, `department_id`, `slug` (unique), `role_summary`, `responsibilities:ARRAY`, `preferred_qualifications:ARRAY`, `reporting_manager`, `work_mode`, `hiring_centre`, `country`, `city`, `timezone`, `visa_sponsorship`, `remote_eligibility`, `interview_process:jsonb`, `equal_opportunity_statement`, `job_benefits:jsonb`, `is_template`, timestamps
- RLS policies: Anyone can view active jobs; Employers can manage their jobs; Super admins manage jobs

### notifications — 0 rows
- `id`, `user_id`, `title`, `message`, `type`, `read`, `data:jsonb`, `created_at`
- RLS policies: Users can update own notifications; Users can view own notifications

### offices — 10 rows
- `id`, `company_id`, `slug` (uq per company), `name`, `country`, `city`, `address`, `timezone`, `is_hiring_centre`, `is_headquarters`, `latitude/longitude:numeric`, `display_order`, `created_at`
- RLS policy: Public read offices

### payments — 0 rows
- `id`, `user_id`, `amount:numeric`, `currency`, `payment_method`, `status`, `transaction_id`, `description`, `created_at`
- RLS policy: Users can view own payments

### profiles — 1 row
- `id`, `email` (unique), `first_name`, `last_name`, `role`, `company_name`, `phone`, `location`, `bio`, `skills:ARRAY`, `experience:jsonb`, `education:jsonb`, `certifications:jsonb`, `desired_salary`, `preferred_locations:ARRAY`, `remote_preference`, `government_id`, `department`, `country`, `business_license`, `tax_id`, `is_verified`, `is_super_admin`, timestamps
- RLS policies: Users can insert/update/view own profile

### saved_jobs — 0 rows
- pk=(`job_id`,`user_id`); RLS: Users manage saved jobs

### talent_pool — 0 rows
- `id`, `company_id`, `candidate_id`, `source`, `notes`, `tags:ARRAY`, `added_at`; uq (company,candidate)
- RLS policy: Super admins manage talent pool

### test_results — 0 rows
- `id`, `user_id`, `job_id`, `test_type`, `score:integer`, `max_score:integer`, `results:jsonb`, `completed_at`
- RLS policies: Users can insert/view own test results

## Storage (read-only)

3 buckets — `kyc-documents`, `kyc-selfies`, `user-documents` — **all private** (`public=false`). Storage-object policies live in Supabase-managed tables not enumerable from this connection; verify from the dashboard before launch (see `PHASE_18_LAUNCH_CHECKLIST.md`).

## Notes

- No row contents were read; counts are metadata only.
- The mislabeled "types" capture in the raw inventory listed relations; the corrected query confirms **0 user-defined enum types** in `public`, so there is no enum-name collision risk with canonical migrations.
- 14 check constraints exist across legacy tables; none reference other tables.
