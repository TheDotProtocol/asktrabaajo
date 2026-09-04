-- ============================================================================
-- AskTrabaajo — least-privilege runtime database role (Phase 13)
--
-- STATUS: GUARDED ARTIFACT — NOT EXECUTED. Run only on a staging/scratch
-- database first, then on the target environment by a superuser/migration
-- role as part of a documented deployment (see PHASE_13_MIGRATION_PLAN.md).
--
-- PURPOSE
--   The canonical backend must NEVER run as the database owner. This script
--   creates the runtime role ``asktrabaajo_app`` with table-level DML on the
--   canonical tables only (no DDL, no superuser, no role management, no
--   legacy schemas). Database-level RLS (migration 0010+) then constrains
--   row access for this role via the per-request session identity
--   (app.current_user_id / app.current_org_ids).
--
-- LEGACY SAFETY
--   Only CANONICAL tables are granted. No legacy Supabase object is touched.
--   The list below is the exact 79-table canonical metadata
--   (Base.metadata, migrations 0001-0014); alembic_version is excluded.
--
-- USAGE (superuser)
--   psql "$DATABASE_URL" -f scripts/db/app_role.sql
--   Then point DATABASE_URL at a connection using this role.
--
-- ROLLBACK
--   REASSIGN OWNED BY asktrabaajo_app TO <owner>; DROP OWNED BY asktrabaajo_app;
--   DROP ROLE asktrabaajo_app;
-- ============================================================================

DO $$
DECLARE
  t TEXT;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'asktrabaajo_app') THEN
    CREATE ROLE asktrabaajo_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
      NOINHERIT CONNECTION LIMIT 50;
  END IF;
  -- Schema access: USAGE only (never ALL — no DDL capability).
  GRANT USAGE ON SCHEMA public TO asktrabaajo_app;
  -- Narrow, canonical-table-only DML.
  REVOKE ALL ON ALL TABLES IN SCHEMA public FROM asktrabaajo_app;
  FOR t IN SELECT tablename FROM pg_tables
           WHERE schemaname = 'public'
             AND tablename IN (
               'ai_interview_evaluations','ai_interview_questions','ai_interview_reports',
               'ai_interview_sessions','ai_usage_log','appeals','application_events',
               'commerce_invoices','commerce_plan_entitlements','commerce_plans',
               'commerce_subscriptions','payment_refunds','payment_transactions',
               'payment_webhook_events','usage_records',
               'athena_action_confirmations','athena_messages','athena_sessions','audit_log',
               'candidate_search_events',
               'career_goals','career_milestones','career_path_steps','career_paths',
               'company_profiles','consents','conversation_messages',
               'conversation_read_states','conversations','credentials',
               'document_access_grants','document_requests','educations',
               'email_verification_tokens','employments','enforcement_actions',
               'governance_case_links','governance_report_notes','governance_reports',
               'governance_team_members','governance_teams','interview_scorecards',
               'interview_prep_sessions','interviews','job_applications','job_postings','memberships',
               'notification_preferences','offers','opportunities',
               'opportunity_interactions','opportunity_requirements','organizations',
               'outreach_blocks','outreach_requests','password_reset_tokens',
               'permissions','person_documents','person_profiles',
               'person_visibility_settings','platform_events','rate_limit_hits',
               'refresh_tokens','role_permissions','roles','saved_candidates',
               'screening_responses','skill_aliases','skill_evidence',
               'skill_relationships','skills','talent_pool_members','talent_pools',
               'user_notifications','user_skills','users','work_dna_answers',
               'work_dna_profiles','work_experiences'
             )
  LOOP
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON public.%I TO asktrabaajo_app', t);
  END LOOP;
END $$;

-- Sequences used by canonical tables.
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO asktrabaajo_app;

-- Explicitly deny the dangerous surfaces (belt and braces; these revokes
-- do NOT remove USAGE on public which was granted above). Each revoke is
-- conditional: on vanilla PostgreSQL those Supabase-only schemas do not
-- exist, and revoking from a missing schema would abort the script.
DO $$
DECLARE
  s TEXT;
BEGIN
  FOREACH s IN ARRAY ARRAY['auth', 'storage', 'graphql', 'realtime', 'supabase_functions']
  LOOP
    IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = s) THEN
      EXECUTE format('REVOKE ALL ON SCHEMA %I FROM asktrabaajo_app', s);
    END IF;
  END LOOP;
END $$;