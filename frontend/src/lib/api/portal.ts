/**
 * Portal routing + permission helpers.
 *
 * Frontend checks are UX only. Backend RBAC remains authoritative.
 * Permission codes come from GET /auth/me (canonical catalog).
 */
import { MeResponse, MembershipBrief } from "./types";

export const GOVERNANCE_PERMISSIONS = [
  "reports.read",
  "enforcement.read",
  "appeals.read",
  "reports.teams",
  "platform.audit.read",
  "admin.manage",
] as const;

export type PostAuthIntent = "jobseeker" | "employer";

export function hasPermission(me: MeResponse | null, code: string): boolean {
  if (!me) return false;
  if (me.super_admin) return true;
  return me.permissions.includes(code);
}

export function hasAnyPermission(
  me: MeResponse | null,
  codes: readonly string[]
): boolean {
  return codes.some((code) => hasPermission(me, code));
}

export function employerMemberships(me: MeResponse | null): MembershipBrief[] {
  if (!me) return [];
  return me.memberships.filter(
    (m) => m.organization_kind === "employer" || m.organization_kind === "recruiter"
  );
}

export function canAccessJobseeker(me: MeResponse | null): boolean {
  return Boolean(me);
}

export function canAccessEmployer(me: MeResponse | null): boolean {
  return employerMemberships(me).length > 0;
}

export function canAccessGovernance(me: MeResponse | null): boolean {
  return hasAnyPermission(me, GOVERNANCE_PERMISSIONS);
}

export function homeForMe(
  me: MeResponse | null,
  intent?: PostAuthIntent | null
): string {
  if (!me) return "/login";
  if (intent === "employer") return "/company";
  if (intent === "jobseeker") return "/jobseeker";
  if (canAccessEmployer(me)) return "/company";
  if (canAccessGovernance(me)) return "/admin/governance";
  return "/jobseeker";
}

export function loginRedirectPath(
  me: MeResponse | null,
  next?: string | null,
  intent?: PostAuthIntent | null
): string {
  if (next && next.startsWith("/") && !next.startsWith("//")) {
    return next;
  }
  return homeForMe(me, intent);
}
