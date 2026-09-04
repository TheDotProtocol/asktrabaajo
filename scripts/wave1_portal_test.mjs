import assert from "node:assert/strict";

function hasPermission(me, code) {
  if (!me) return false;
  if (me.super_admin) return true;
  return me.permissions.includes(code);
}

function hasAnyPermission(me, codes) {
  return codes.some((code) => hasPermission(me, code));
}

function employerMemberships(me) {
  if (!me) return [];
  return me.memberships.filter(
    (m) => m.organization_kind === "employer" || m.organization_kind === "recruiter"
  );
}

function canAccessEmployer(me) {
  return employerMemberships(me).length > 0;
}

function canAccessGovernance(me) {
  return hasAnyPermission(me, [
    "reports.read",
    "enforcement.read",
    "appeals.read",
    "reports.teams",
    "platform.audit.read",
    "admin.manage",
  ]);
}

function homeForMe(me, intent) {
  if (!me) return "/login";
  if (intent === "employer") return "/company";
  if (intent === "jobseeker") return "/jobseeker";
  if (canAccessEmployer(me)) return "/company";
  if (canAccessGovernance(me)) return "/admin/governance";
  return "/jobseeker";
}

function loginRedirectPath(me, next, intent) {
  if (next && next.startsWith("/") && !next.startsWith("//")) return next;
  return homeForMe(me, intent);
}

function me(partial = {}) {
  return {
    user_id: "u1",
    email: "a@example.com",
    full_name: "A",
    status: "active",
    email_verified: false,
    mfa_enabled: false,
    person: null,
    memberships: [],
    permissions: [],
    super_admin: false,
    ...partial,
  };
}

assert.equal(homeForMe(null), "/login");
assert.equal(homeForMe(me()), "/jobseeker");
assert.equal(homeForMe(me(), "employer"), "/company");
assert.equal(
  homeForMe(
    me({
      memberships: [
        {
          organization_id: "o1",
          organization_name: "Acme",
          organization_slug: "acme",
          organization_kind: "employer",
          role: "org_admin",
        },
      ],
    })
  ),
  "/company"
);
assert.equal(homeForMe(me({ permissions: ["reports.read"] })), "/admin/governance");
assert.equal(loginRedirectPath(me(), "/jobseeker/applications"), "/jobseeker/applications");
assert.equal(loginRedirectPath(me(), "https://evil.example"), "/jobseeker");
assert.equal(hasPermission(me({ super_admin: true }), "finance.manage"), true);
assert.equal(hasPermission(me({ permissions: ["jobs.view"] }), "jobs.view"), true);
assert.equal(hasPermission(me({ permissions: ["jobs.view"] }), "finance.manage"), false);
assert.equal(
  canAccessEmployer(
    me({
      memberships: [
        {
          organization_id: "o1",
          organization_name: "Acme",
          organization_slug: "acme",
          organization_kind: "employer",
          role: "hr",
        },
      ],
    })
  ),
  true
);
assert.equal(canAccessGovernance(me({ permissions: ["reports.read"] })), true);
assert.equal(canAccessGovernance(me()), false);

console.log("wave1 portal tests: PASS");
