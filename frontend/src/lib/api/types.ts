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
