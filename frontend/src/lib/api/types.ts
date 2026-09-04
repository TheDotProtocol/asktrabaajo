/**
 * Canonical API contract types — mirror the FastAPI /api/v1 schemas.
 * Full codegen from OpenAPI lands with the endpoint migrations (P5+).
 */

export interface ApiErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}

export interface ApiEnvelope {
  error: ApiErrorDetail;
}

export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in_seconds: number;
}

export interface LoginResult {
  mfa_required: boolean;
  mfa_token?: string | null;
  access_token?: string | null;
  refresh_token?: string | null;
  token_type: string;
  expires_in_seconds?: number | null;
}

export interface PersonSummary {
  id: string;
  headline: string | null;
  summary: string | null;
  location: string | null;
  country_code: string | null;
}

export interface MembershipBrief {
  organization_id: string;
  organization_name: string;
  organization_slug: string;
  organization_kind: "employer" | "recruiter" | "government" | "platform";
  role: string;
}

export interface MeResponse {
  user_id: string;
  email: string;
  full_name: string;
  status: string;
  email_verified: boolean;
  mfa_enabled: boolean;
  person: PersonSummary | null;
  memberships: MembershipBrief[];
  permissions: string[];
  super_admin: boolean;
}

export interface MessageResponse {
  message: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  kind: "employer" | "recruiter" | "government" | "platform";
  status: string;
  created_at: string;
}

export interface WorkIdSummary {
  person: ProfileOut;
  experiences: ExperienceOut[];
  educations: EducationOut[];
  skills: UserSkillOut[];
  credentials: CredentialOut[];
  employments: EmploymentOut[];
}

export interface ProfileOut {
  id: string;
  headline: string | null;
  summary: string | null;
  preferred_name: string | null;
  city: string | null;
  state_province: string | null;
  location: string | null;
  country_code: string | null;
  phone: string | null;
  updated_at: string;
}

export interface ExperienceOut {
  id: string;
  company_name: string;
  title: string;
  department: string | null;
  location: string | null;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  verification_status: string;
}

export interface EducationOut {
  id: string;
  institution: string;
  level: string | null;
  degree: string | null;
  start_date: string | null;
  end_date: string | null;
  is_current: boolean;
  verification_status: string;
}

export interface UserSkillOut {
  id: string;
  skill_id: string;
  name: string;
  level: string;
  years_experience: number | null;
}

export interface CredentialOut {
  id: string;
  name: string;
  issuer: string | null;
  credential_type: string;
  status: string;
  issued_at: string | null;
  expires_at: string | null;
  verified_at: string | null;
}

export interface EmploymentOut {
  id: string;
  company_name: string;
  title: string;
  department: string | null;
  employment_type: string;
  start_date: string;
  end_date: string | null;
  is_current: boolean;
  verification_status: string;
}

export interface CompletionOut {
  percent: number;
  missing: string[];
}

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
}

// --- Jobseeker Career OS (Phase 5) -------------------------------------------

export interface DnaQuestion {
  key: string;
  question: string;
  options: { value: string; label: string }[];
}

export interface DnaDimension {
  key: string;
  label: string;
  signal: number;
  confidence: number;
}

export interface DnaProfile {
  id: string;
  version: string;
  source: string;
  status: string;
  dimensions: DnaDimension[] | null;
  completed_at: string | null;
}

export interface CareerGoal {
  id: string;
  title: string;
  target_role: string | null;
  target_industries: string[] | null;
  target_locations: string[] | null;
  preferred_work_modes: string[] | null;
  min_salary: number | null;
  salary_currency: string | null;
  open_to_relocation: boolean;
  open_to_remote: boolean;
  availability: string | null;
  is_primary: boolean;
  status: string;
}

export interface Opportunity {
  id: string;
  company_name: string;
  title: string;
  summary: string | null;
  country: string | null;
  city: string | null;
  remote_eligible: boolean;
  work_mode: string | null;
  employment_type: string | null;
  experience_level: string | null;
  seniority: string | null;
  industry: string | null;
  skills_required: string[] | null;
  min_salary: number | null;
  max_salary: number | null;
  salary_currency: string | null;
}

export interface MatchComponent {
  score: number;
  reason: string;
  matched?: string[] | null;
  missing?: string[] | null;
}

export interface OpportunityMatch {
  opportunity_id: string;
  percent: number;
  score: number;
  components: Record<string, MatchComponent>;
  strengths: string[];
  gaps: string[];
  missing_skills: string[];
  opportunity: Opportunity | null;
  saved: boolean;
  applied: boolean;
}

export interface OpportunityList {
  items: OpportunityMatch[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApplicationEvent {
  id: string;
  from_status: string | null;
  to_status: string;
  note: string | null;
  created_at: string;
}

export interface JobApplication {
  id: string;
  opportunity_id: string;
  status: string;
  cover_note: string | null;
  applied_at: string | null;
  last_activity_at: string;
  opportunity: Opportunity | null;
}

export interface ApplicationDetail {
  application: JobApplication;
  timeline: ApplicationEvent[];
  opportunity: Opportunity | null;
  has_interview: boolean;
  has_offer: boolean;
}

export interface Interview {
  id: string;
  application_id: string;
  scheduled_at: string;
  duration_minutes: number;
  mode: string;
  meeting_link: string | null;
  interviewer_name: string | null;
  status: string;
  reschedule_reason: string | null;
  reschedule_count: number;
}

export interface Offer {
  id: string;
  application_id: string;
  status: string;
  salary_amount: number | null;
  salary_currency: string | null;
  equity: string | null;
  benefits_summary: string | null;
  start_date: string | null;
  location: string | null;
  terms_summary: string | null;
  responded_at: string | null;
  expires_at: string | null;
}

export interface AdvisorGap {
  kind: string;
  title: string;
  detail: string;
  skill: string | null;
  action_type: string | null;
}

export interface AdvisorSnapshot {
  summary: string;
  current_position: { title: string | null; company: string | null };
  roles_held: string[];
  strongest_skills: string[];
  career_goal: { id: string | null; title: string | null; target_role: string | null };
  gaps: AdvisorGap[];
  learning_recommendations: {
    skill: string;
    recommendation: string;
    kind: string;
  }[];
  next_actions: string[];
  disclaimer: string;
}

export interface Dashboard {
  profile_completion: { percent: number; missing: string[] } | null;
  work_dna_status: string;
  has_career_goal: boolean;
  stats: Record<string, number>;
  upcoming_interviews: Interview[];
  recent_applications: JobApplication[];
  recommended: OpportunityMatch[];
  advisor: AdvisorSnapshot | null;
  unread_notifications: number;
}

export interface UserNotification {
  id: string;
  kind: string;
  title: string;
  body: string | null;
  read_at: string | null;
  created_at: string;
}

export interface CareerMilestone {
  id: string;
  kind: string;
  title: string;
  occurred_on: string;
  description: string | null;
}

// --- Company / Employer OS (Phase 6) -----------------------------------------

export interface MyOrganization {
  organization_id: string;
  name: string;
  slug: string;
  kind: "employer" | "recruiter" | "government" | "platform";
  status: string;
  role: string;
}

export interface CompanyProfile {
  organization_id: string;
  legal_name: string | null;
  display_name: string | null;
  industry: string | null;
  sector: string | null;
  country: string | null;
  city: string | null;
  website_url: string | null;
  company_size: string | null;
  company_type: string | null;
  description: string | null;
  contact_name: string | null;
  contact_email: string | null;
  verification_status: string;
}

export interface CompanyDashboard {
  organization: { id: string; name: string; slug: string; kind: string };
  profile: CompanyProfile | null;
  open_jobs: number;
  applications_total: number;
  needs_review: number;
  interviews_today: number;
  interviews_upcoming: number;
  offers_pending: number;
  offers_accepted: number;
  recent_applications: {
    id: string;
    status: string;
    job_title: string | null;
    applied_at: string | null;
    candidate_name: string;
  }[];
  my_role: string;
  permissions: string[];
}

export interface CompanyJob {
  id: string;
  organization_id: string;
  opportunity_id: string | null;
  title: string;
  slug: string;
  department: string | null;
  summary: string | null;
  description: string | null;
  requirements: string[] | null;
  skills_required: string[] | null;
  preferred_skills: string[] | null;
  experience_level: string | null;
  location: string | null;
  country: string | null;
  city: string | null;
  remote_eligible: boolean;
  work_mode: string | null;
  employment_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  seniority: string | null;
  industry: string | null;
  openings_count: number;
  status: string;
  published_at: string | null;
  applications_count: number;
}

export interface CompanyApplication {
  id: string;
  status: string;
  job_id: string | null;
  opportunity_id: string | null;
  job_title: string | null;
  candidate_name: string;
  applied_at: string | null;
  last_activity_at: string | null;
}

export interface ApplicationEventRow {
  id: string;
  from_status: string | null;
  to_status: string;
  note: string | null;
  created_at: string;
}

export interface CandidateReview {
  person: Record<string, unknown>;
  skills: { id?: string; name: string; level: string; years_experience?: number | null }[];
  has_live_consent: boolean;
  disclosure: Record<string, boolean>;
  application_events_count: number;
  events: ApplicationEventRow[];
}

export interface ApplicationReview {
  application: {
    id: string;
    status: string;
    opportunity_id: string | null;
    job_id: string | null;
    cover_note: string | null;
    applied_at: string | null;
    last_activity_at: string | null;
  };
  job: { id: string | null; title: string | null } | null;
  candidate: CandidateReview | null;
  interview: {
    id: string;
    scheduled_at: string;
    status: string;
    mode: string;
    interviewer_name: string | null;
  } | null;
  offer: {
    id: string;
    status: string;
    salary_amount: number | null;
    salary_currency: string | null;
  } | null;
}

export interface CompanyAnalytics {
  open_jobs: number;
  total_jobs: number;
  applications_total: number;
  by_status: Record<string, number>;
  needs_review: number;
  interviews_scheduled: number;
  offers_pending: number;
  conversion: Record<string, number>;
}

export interface DocumentRequestRow {
  id: string;
  application_id: string;
  organization_id: string;
  document_type: string;
  purpose: string | null;
  status: string;
  note: string | null;
  created_at: string;
}

export interface CompanyOffer {
  id: string;
  application_id: string;
  status: string;
  salary_amount: number | null;
  salary_currency: string | null;
  responded_at: string | null;
}

export interface CompanyInterview {
  id: string;
  application_id: string;
  scheduled_at: string;
  status: string;
  mode: string;
  interviewer_name: string | null;
  duration_minutes: number;
  reschedule_count: number;
}

// --- Talent Graph (Phase 7) ---------------------------------------------------

export interface TaxonomySkill {
  id: string;
  name: string;
  category: string;
  subcategory: string | null;
  description: string | null;
  status: string;
}

export interface TaxonomyList {
  total: number;
  page: number;
  page_size: number;
  categories: string[];
  items: TaxonomySkill[];
}

export interface SkillDetail {
  id: string;
  name: string;
  category: string;
  subcategory: string | null;
  description: string | null;
  status: string;
  aliases: string[];
  parents: { kind: string; name: string }[];
  related: { kind: string; name: string }[];
}

export interface NormalizeResult {
  raw: string;
  normalized: string;
  canonical: { id: string; name: string } | null;
}

export interface SkillSummary {
  name: string;
  level: string | null;
}

export interface Disclosure {
  profile: boolean;
  skills_visible: boolean;
  experience_visible: boolean;
  contact_visible: boolean;
}

export interface LatestRole {
  title: string;
  company_name: string;
  is_current: boolean;
}

export interface CandidateSearchItem {
  person_id: string;
  name: string | null;
  headline: string | null;
  location: string | null;
  skills: SkillSummary[];
  experience_years: number | null;
  latest_role: LatestRole | null;
  disclosure: Disclosure;
}

export interface CandidateSearchList {
  items: CandidateSearchItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface MatchedCandidate {
  person_id: string;
  summary: CandidateSearchItem;
  percent: number;
  score: number;
  mode: string;
  coverage: number;
  strengths: string[];
  gaps: string[];
  matched_skills: string[];
  missing_skills: string[];
}

export interface MatchedCandidateList {
  items: MatchedCandidate[];
  total: number;
  page: number;
  page_size: number;
  opportunity_id: string;
}

export interface SavedCandidate {
  id: string;
  person_id: string;
  name: string | null;
  headline: string | null;
  note: string | null;
  tags: string[] | null;
  saved_at: string;
  context: string;
}

export interface TalentPool {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  member_count: number;
}

export interface PoolMember {
  person_id: string;
  name: string | null;
  headline: string | null;
  note: string | null;
  added_at: string;
}

export interface TalentPoolDetail {
  id: string;
  name: string;
  description: string | null;
  member_count: number;
  members: PoolMember[];
}

export interface OpportunityRequirementRow {
  id: string;
  skill: string | null;
  raw_text: string;
  requirement_kind: string;
  min_years: number | null;
}

export interface EvidenceRow {
  evidence_type: string;
  verification_status: string;
}

export interface GapAnalysis {
  matched: { skill: string; evidence: EvidenceRow[] }[];
  gaps: { skill: string; source: string }[];
  coverage: number;
}

/** Discovery-safe candidate profile payload (progressive disclosure). */
export interface CandidateProfile {
  person_id: string;
  context: string;
  saved: boolean;
  pool_names: string[];
  name?: string | null;
  headline?: string | null;
  location?: string | null;
  skills?: { name: string; level?: string | null }[] | null;
  experience_years?: number | null;
  latest_role?: LatestRole | null;
  experience?: { company_name: string; title: string; is_current: boolean }[] | null;
  education?: { institution: string; level: string | null; degree: string | null }[] | null;
  disclosure?: Disclosure | null;
  person?: { full_name?: string | null; headline?: string | null; location?: string | null } | null;
  match?: {
    percent: number;
    score: number;
    mode: string;
    strengths: string[];
    gaps: string[];
    matched_skills: string[];
    missing_skills: string[];
    gap_analysis: GapAnalysis;
  } | null;
  has_live_consent?: boolean;
}

export interface JobseekerOpportunityDetail {
  opportunity: Opportunity;
  match: OpportunityMatch | null;
  gap_analysis: GapAnalysis;
  requirements: OpportunityRequirementRow[];
  saved: boolean;
  applied: boolean;
  stance: string | null;
}

export interface CareerIntelligence {
  capability: {
    years_experience: number;
    roles_held: number;
    skills: {
      name: string;
      level: string;
      years_experience: number | null;
      evidence_count: number;
    }[];
    verified_skill_count: number;
  };
  current_position: { title: string | null; company: string | null; is_current: boolean };
  career_goal: { title: string | null; target_role: string | null };
  roles_within_reach: CareerRoleRow[];
  roles_to_grow_into: CareerRoleRow[];
  skill_development: { skill: string; appears_in_roles: number }[];
  path_advice: {
    path: string;
    target_role: string;
    current_step?: string | null;
    next_step?: {
      role_title: string;
      seniority: string | null;
      description: string | null;
      typical_skills: string[] | null;
    } | null;
    note: string;
  } | null;
  disclaimer: string;
}

export interface CareerRoleRow {
  opportunity_id: string;
  title: string | null;
  company: string | null;
  percent: number;
  strengths: string[];
  missing_skills: string[];
}

/* ----------------------------- Phase 8: outreach + communications ----------------------------- */

export interface OutreachRequestRow {
  id: string;
  organization_id?: string;
  organization_name?: string | null;
  candidate?: { person_id: string; name: string | null; headline: string | null } | null;
  opportunity_id?: string | null;
  opportunity_title?: string | null;
  application_id?: string | null;
  message: string;
  context?: string | null;
  status: string;
  requester_id?: string;
  requester_name?: string | null;
  created_at: string | null;
  expires_at: string | null;
  viewed_at?: string | null;
  responded_at: string | null;
  note?: string | null;
  conversation_id?: string | null;
  organization?: { id: string; name: string | null } | null;
  opportunity?: { id: string; title: string | null; company: string | null } | null;
}

export interface ConversationMessageRow {
  id: string;
  conversation_id: string;
  sender_user_id: string;
  sender_side: string;
  sender_name: string | null;
  body: string;
  created_at: string | null;
}

export interface ConversationRow {
  id: string;
  organization: { id: string; name: string | null };
  candidate: { person_id: string; name: string | null };
  counterpart: string | null;
  opportunity_id: string | null;
  opportunity_title: string | null;
  application_id: string | null;
  outreach_id: string | null;
  status: string;
  created_at: string | null;
  last_message_at: string | null;
  closed_at: string | null;
  unread_count: number;
  messages: ConversationMessageRow[] | null;
}

export interface CommunicationsInbox {
  outreach: OutreachRequestRow[];
  conversations: ConversationRow[];
  unread: { unread_messages: number; pending_outreach: number };
}

export interface BlockedOrg {
  organization_id: string;
  organization_name: string | null;
  reason: string | null;
  created_at: string | null;
}

// --- Phase 9: platform governance ---------------------------------------------

export interface GovernanceCaseLinkRow {
  link_id: string;
  report_id: string;
  case_ref: string;
  category: string;
  severity: string;
  status: string;
  created_at: string | null;
  reason: string | null;
}

export interface GovernanceReportRow {
  id: string;
  case_ref: string | null;
  reporter_user_id: string;
  target_type: string;
  target_id: string;
  organization_id: string | null;
  organization_name: string | null;
  category: string;
  severity: string;
  priority: string | null;
  status: string;
  description: string;
  evidence_refs: Array<{ type: string; id: string; note?: string | null }>;
  assigned_moderator_id: string | null;
  assigned_moderator_name: string | null;
  team_id: string | null;
  team_name: string | null;
  team_slug: string | null;
  escalated_at: string | null;
  escalated_to_team_id: string | null;
  escalated_to_team_name: string | null;
  first_responded_at: string | null;
  sla_response_due_at: string | null;
  sla_resolution_due_at: string | null;
  sla_state: string | null;
  resolution: string | null;
  resolved_at: string | null;
  reopened_count: number;
  created_at: string | null;
  updated_at: string | null;
  notes?: Array<{
    id: string;
    author_user_id: string;
    body: string;
    created_at: string | null;
  }> | null;
  links?: GovernanceCaseLinkRow[] | null;
  audit?: Array<{
    action: string;
    actor_id: string | null;
    result: string | null;
    created_at: string | null;
    payload: Record<string, unknown> | null;
  }> | null;
}

export interface GovernanceQueue {
  items: GovernanceReportRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface GovernanceDashboard {
  total: number;
  open: number;
  urgent: number;
  critical: number;
  unassigned: number;
  mine: number;
  escalated: number;
  breached: number;
  due_soon: number;
  recently_resolved: number;
  by_status: Record<string, number>;
  by_severity: Record<string, number>;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  by_team: Record<string, number>;
}

export interface GovernanceTeamRow {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  member_count: number;
  open_cases: number;
}

export interface GovernanceTeamDetail {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  members: Array<{ user_id: string; full_name: string; joined_at: string | null }>;
  counts: {
    open: number;
    urgent: number;
    breached: number;
    unresolved: number;
  };
}

export interface GovernanceModeratorRow {
  user_id: string;
  full_name: string;
  roles: string[];
}

export interface GovernanceAuditRow {
  id: string;
  action: string;
  actor_id: string | null;
  actor_name: string | null;
  resource_type: string | null;
  resource_id: string | null;
  organization_id: string | null;
  result: string | null;
  request_id: string | null;
  created_at: string | null;
  payload: Record<string, unknown>;
}

export interface GovernanceAuditPage {
  items: GovernanceAuditRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface IntegritySignalRow {
  signal_type: string;
  subject_type: string;
  subject_id: string;
  subject_name?: string | null;
  count: number;
  window_days: number;
  status: string;
  note: string;
}

// --- Phase 9: realtime event feed ---------------------------------------------

export interface PlatformEventRow {
  id: string;
  event_type: string;
  resource_type: string;
  resource_id: string;
  organization_id: string | null;
  payload: Record<string, unknown>;
  read: boolean;
  created_at: string | null;
}

export interface EventsFeed {
  items: PlatformEventRow[];
  count: number;
  next_after: string | null;
}

// --- Phase 11: moderator enforcement + appeals ---------------------------------

export interface AuditTimelineEntry {
  action: string;
  result: string | null;
  actor_id: string | null;
  created_at: string | null;
  payload: Record<string, unknown> | null;
}

export interface EnforcementActionRow {
  id: string;
  governance_case_id: string | null;
  target_user_id: string | null;
  target_organization_id: string | null;
  action_type: string;
  scope: string;
  reason_code: string;
  status: string;
  stored_status: string;
  created_by: string;
  approved_by: string | null;
  effective_at: string;
  expires_at: string | null;
  activated_at: string | null;
  revoked_at: string | null;
  supersedes_id: string | null;
  note: string | null;
  created_at: string | null;
  audit?: AuditTimelineEntry[] | null;
}

export interface EnforcementActionList {
  items: EnforcementActionRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface AppealRow {
  id: string;
  enforcement_action_id: string;
  appellant_user_id: string;
  reason_code: string;
  statement: string | null;
  status: string;
  assigned_reviewer_id: string | null;
  decision: string | null;
  decision_note: string | null;
  review_note: string | null;
  decided_by: string | null;
  decided_at: string | null;
  withdrawn_at: string | null;
  superseding_action_id: string | null;
  created_at: string | null;
  updated_at: string | null;
  audit?: AuditTimelineEntry[] | null;
}

export interface AppealList {
  items: AppealRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface DerivedPlatformState {
  user_id: string;
  state: string;
  active_restrictions: Array<{
    id: string;
    action_type: string;
    scope: string;
    reason_code: string;
    expires_at: string | null;
  }>;
  derived_at: string;
}

// --- Phase 15: Career Advisor + Interview Preparation -------------------------

export interface CareerDigest {
  person_id: string;
  professional_summary: string;
  current_position: { title: string | null; company: string | null };
  experience_summary: {
    roles_held: number;
    years_experience: number;
    recent_roles: Array<{
      title: string;
      company: string;
      start_date: string | null;
      end_date: string | null;
      current: boolean;
    }>;
  };
  education_summary: Array<{
    level: string | null;
    degree: string | null;
    institution: string | null;
    field: string | null;
  }>;
  credentials: {
    verified: Array<{ name: string; issuer: string | null }>;
    unverified: Array<{ name: string; issuer: string | null; status: string }>;
    note: string;
  };
  skills: {
    all: Array<{ name: string; level: string }>;
    strongest: Array<{ name: string; level: string }>;
  };
  career_goal: {
    title: string | null;
    target_role: string | null;
    target_industries: string[];
    target_locations: string[];
    preferred_work_modes: string[];
    availability: string | null;
  };
  career_milestones: Array<{
    title: string;
    kind: string;
    occurred_on: string | null;
  }>;
  application_status_counts: Record<string, number>;
  disclaimer: string;
}

export interface CareerSkillGap {
  skill: string;
  status: string;
  note?: string;
  related_skills?: string[];
  level?: string;
}

export interface CareerGaps {
  target: Record<string, unknown> | null;
  target_kind: string;
  required_skill_count: number;
  matched_skills: CareerSkillGap[];
  partial_skills: CareerSkillGap[];
  missing_skills: CareerSkillGap[];
  skill_coverage: number | null;
  experience_gap: Record<string, unknown> | null;
  credential_gap: Record<string, unknown> | null;
  summary: string;
  disclaimer: string;
}

export interface CareerPathView {
  path: string;
  target_role: string;
  classification: string;
  current_step: string | null;
  steps: string[];
  next_step: {
    role_title: string | null;
    seniority?: string | null;
    description?: string | null;
  } | null;
  gap_to_next_step?: { from_role: string; to_role: string } | null;
  note?: string;
}

export interface CareerPaths {
  anchor: string | null;
  anchored_from: string | null;
  paths: CareerPathView[];
  disclaimer: string;
}

export interface CareerRecommendation {
  opportunity_id: string;
  title: string;
  company: string;
  location: string | null;
  country: string | null;
  work_mode: string | null;
  seniority: string | null;
  percent: number;
  strengths: string[];
  missing_skills: string[];
  career_signal: { signals: string[] } | null;
}

export interface CareerRecommendations {
  mode: string;
  count: number;
  items: CareerRecommendation[];
  note: string;
  disclaimer: string;
}

export interface ApplicationAnalysis {
  application_count: number;
  applied_count: number;
  advanced_count: number;
  status_counts: Record<string, number>;
  outcome_counts: Record<string, number>;
  movement_rate: number | null;
  movement_note: string;
  stuck_applications: Array<{
    application_id: string;
    company: string;
    title: string | null;
    days: number;
  }>;
  top_companies: Array<{ company: string; applications: number }>;
  advice: string[];
}

export interface CareerActionPlan {
  goal: {
    title: string | null;
    target_role: string | null;
  };
  current_state: Record<string, unknown>;
  gap_summary: string;
  actions: Array<{
    type: string;
    title: string;
    detail?: string;
    target_week: number;
  }>;
  milestone_suggestions: Array<{
    kind: string;
    title: string;
    occurred_on: string;
    suggested: boolean;
  }>;
  note: string;
}

export interface PrepSession {
  id: string;
  status: string;
  opportunity_id: string | null;
  application_id: string | null;
  interview_id: string | null;
  focus_areas: string[];
  questions_generated: number;
  answers_evaluated: number;
  created_at: string | null;
  expires_at: string | null;
  completed_at: string | null;
}

export interface PrepQuestion {
  question: string;
  category: string;
  competency: string;
  difficulty: string;
  reason: string;
  target_skill: string | null;
  suggested_answer_dimensions: string[];
}

export interface PrepQuestions {
  session_id: string;
  count: number;
  questions: PrepQuestion[];
  note: string;
}

export interface AnswerDimension {
  score: number;
  explanation: string;
}

export interface AnswerEvaluation {
  session_id: string;
  dimensions: Record<string, AnswerDimension>;
  what_you_did_well: string[];
  what_was_missing: string[];
  how_to_improve: string[];
  stronger_response_pointer: string;
  disclaimer: string;
}

// --- Phase 16 — AI Interview Engine -------------------------------------------

export interface AiInterviewSessionView {
  session_id: string;
  status: string;
  interview_type: string;
  language: string;
  duration_minutes: number;
  question_count: number;
  difficulty: string;
  opportunity_title?: string | null;
  company_name?: string | null;
  consent_required: boolean;
  consent_granted: boolean;
  consent_mic: boolean;
  consent_camera: boolean;
  consent_recording: boolean;
  media_profile?: Record<string, unknown>;
  voice_enabled: boolean;
  video_enabled: boolean;
  started_at: string | null;
  completed_at: string | null;
  expires_at: string | null;
  created_at?: string | null;
  note?: string;
}

export interface AiInterviewCreateResult {
  session_id: string;
  entry_token: string;
  expires_at: string | null;
}

export interface AiInterviewStartOut {
  session_id: string;
  status: string;
  introduction: string;
  closing: string;
  question_count: number;
  duration_minutes: number;
}

export interface AiInterviewQuestionOut {
  session_id: string;
  question_id: string;
  sequence: number;
  category: string;
  competency: string;
  question: string;
  difficulty: string;
  target_skill: string | null;
  reason: string | null;
  suggested_dimensions: string[];
  is_follow_up: boolean;
  rephrased?: boolean;
  note?: string;
}

export interface AiInterviewDimension {
  score: number;
  explanation: string;
}

export interface AiInterviewEvaluationOut {
  dimensions: Record<string, AiInterviewDimension>;
  strengths: string[];
  improvements: string[];
  evidence_markers: string[];
  disclaimer: string;
}

export interface AiInterviewResponseOut {
  session_id: string;
  evaluation?: AiInterviewEvaluationOut;
  next: AiInterviewQuestionOut | null;
  status?: string;
  reason?: string;
  note?: string;
}

export interface AiInterviewReport {
  session_id: string;
  summary: string;
  competency_evidence?: unknown[];
  strengths?: string[];
  improvement_areas?: string[];
  unanswered_areas?: string[];
  interview_quality?: {
    answered: number;
    total_questions: number;
    completion_pct: number;
    average_dimension_score: number | null;
    note: string;
  };
  integrity_signals?: Array<Record<string, string>>;
  disclaimer: string;
  decision?: string | null;
  decision_note?: string | null;
}

export interface AiInterviewCandidateFeedback {
  session_id: string;
  status: string;
  completed_at: string | null;
  strengths: string[];
  preparation_areas: string[];
  note: string;
}

// --- Phase 17: Commerce / billing / entitlements -------------------------------

export interface BillingPlan {
  plan_id: string;
  code: string;
  name: string;
  description: string | null;
  billing_interval: string;
  currency: string;
  price: string;
  published: boolean;
  seat_included: number;
}

export interface SubscriptionOut {
  subscription_id: string;
  organization_id: string;
  plan_code: string | null;
  plan_name: string | null;
  status: string;
  billing_interval: string;
  currency: string;
  price: string;
  seat_count: number;
  trial_ends_at: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  usage?: Record<string, number>;
}

export interface EntitlementState {
  limit: string | null;
  used: number;
  remaining: number | null;
  unlimited: boolean;
  within_limit: boolean;
}

export interface InvoiceOut {
  invoice_id: string;
  organization_id: string;
  invoice_number: string;
  currency: string;
  subtotal: string;
  tax: string;
  total: string;
  status: string;
  items: Array<{ description: string; amount: string; quantity: number }>;
  issued_at: string | null;
  paid_at: string | null;
}

export interface BillingData {
  plans: BillingPlan[];
  subscription: SubscriptionOut | null;
  entitlements: Record<string, EntitlementState>;
  usage: Record<string, number>;
  invoices: InvoiceOut[];
}

export interface PersonDocumentOut {
  id: string;
  name: string;
  doc_type: string;
  storage_key: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  verification_status: string;
  created_at: string;
}

export interface DocumentGrantOut {
  id: string;
  document_id: string;
  grantee_user_id: string | null;
  grantee_organization_id: string | null;
  purpose: string | null;
  granted_at: string;
  expires_at: string | null;
  revoked_at: string | null;
}

export interface PrivacySettingsOut {
  settings: Record<string, string>;
  allowed_values: string[];
  scopes: string[];
}

export interface CareerAdvisorRecItem {
  opportunity_id: string;
  title: string;
  company: string;
  location?: string | null;
  country?: string | null;
  work_mode?: string | null;
  seniority?: string | null;
  percent: number;
  strengths: string[];
  missing_skills: string[];
  career_signal?: { signals: string[] } | null;
}

export interface CareerAdvisorOpportunities {
  mode: string;
  count: number;
  items: CareerAdvisorRecItem[];
  note: string;
  disclaimer: string;
}

export interface CareerAdvisorDigest {
  professional_summary?: string;
  current_position?: { title: string | null; company: string | null };
  experience_summary?: { roles_held: number; years_experience: number };
  strongest_skills?: string[];
  disclaimer?: string;
}

export interface CareerAdvisorGaps {
  target?: { kind?: string; title?: string | null; target_role?: string | null };
  matched_skills?: { skill: string; level?: string }[];
  partial_skills?: { skill: string; related_skills?: string[]; note?: string }[];
  missing_skills?: { skill: string; note?: string }[];
  disclaimer?: string;
}

export interface CareerAdvisorPath {
  path?: string;
  title?: string;
  classification?: string;
  target_role?: string | null;
  note?: string;
}

export interface CareerAdvisorPaths {
  anchor?: string | null;
  paths?: CareerAdvisorPath[];
  note?: string;
}

export interface CareerAdvisorActionPlan {
  actions?: { type: string; title: string; detail?: string | null; target_week?: number }[];
  disclaimer?: string;
}
