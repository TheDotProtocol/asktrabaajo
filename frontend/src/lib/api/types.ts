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
  person: PersonSummary | null;
  memberships: MembershipBrief[];
  permissions: string[];
  super_admin: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  kind: "employer" | "recruiter" | "government" | "platform";
  status: string;
  created_at: string;
}

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
}
