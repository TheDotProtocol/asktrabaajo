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
