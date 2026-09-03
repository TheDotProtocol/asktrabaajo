"""Role + permission catalog (seed data).

The catalog is small and intentional — roles and permissions grow with the
product, not speculatively. ``seed_catalog`` is idempotent and is called by
the isolated test harness and by the initial Alembic migration.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.tenancy import (
    ROLE_SCOPE_GOVERNMENT,
    ROLE_SCOPE_ORGANIZATION,
    ROLE_SCOPE_PLATFORM,
    Membership,
    Permission,
    Role,
    RolePermission,
)

ROLES = [
    # --- Platform scope -------------------------------------------------------
    ("super_admin", "Super Admin", ROLE_SCOPE_PLATFORM,
     "Platform-wide administration; every action is audited."),
    ("customer_support", "Customer Support", ROLE_SCOPE_PLATFORM,
     "Company/org accounts, plans, billing views, support tickets."),
    ("tech_support", "Tech Support", ROLE_SCOPE_PLATFORM,
     "Auth diagnostics, sessions, MFA. Never views passwords."),
    ("marketing", "Marketing", ROLE_SCOPE_PLATFORM,
     "Campaigns and aggregated audience intelligence."),
    ("finance", "Finance", ROLE_SCOPE_PLATFORM,
     "Employer billing, invoices, payments, refunds, reports."),
    # --- Organization scope ---------------------------------------------------
    ("org_admin", "Organization Admin", ROLE_SCOPE_ORGANIZATION,
     "Company/org settings, members, jobs, pipeline, billing view."),
    ("hr", "HR", ROLE_SCOPE_ORGANIZATION,
     "Jobs, applications, pipeline, offers, AI screening."),
    ("recruiter", "Recruiter", ROLE_SCOPE_ORGANIZATION,
     "Candidate discovery and outreach."),
    ("hiring_manager", "Hiring Manager", ROLE_SCOPE_ORGANIZATION,
     "Review assigned applications and interviews."),
    # --- Government scope -----------------------------------------------------
    ("government_admin", "Government Admin", ROLE_SCOPE_GOVERNMENT,
     "Authorized government dataset scopes; aggregate-only intelligence."),
    ("government_user", "Government Analyst", ROLE_SCOPE_GOVERNMENT,
     "Read workforce aggregates within authorized scopes."),
]

PERMISSIONS = [
    ("users.read", "Read user records"),
    ("users.update", "Update user records"),
    ("orgs.read", "Read organization records"),
    ("orgs.update", "Update organization records"),
    ("members.read", "Read organization members"),
    ("members.manage", "Manage organization members"),
    ("jobs.create", "Create jobs"),
    ("jobs.read", "Read jobs"),
    ("jobs.update", "Update jobs"),
    ("candidates.read", "Read candidate data"),
    ("candidates.update", "Update candidate data"),
    ("interviews.create", "Create interviews"),
    ("interviews.read", "Read interviews"),
    ("billing.read", "Read billing data"),
    ("billing.manage", "Manage billing"),
    ("support.read", "Read support data"),
    ("marketing.manage", "Manage marketing"),
    ("audit.read", "Read audit logs"),
    ("sessions.manage", "Manage user sessions"),
    ("workforce.aggregates.read", "Read aggregated workforce intelligence"),
    ("admin.manage", "Platform administration"),
]

ALL_PERMISSION_CODES = [code for code, _ in PERMISSIONS]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "super_admin": ALL_PERMISSION_CODES,
    "customer_support": ["users.read", "orgs.read", "support.read", "billing.read"],
    "tech_support": ["users.read", "users.update", "sessions.manage", "audit.read"],
    "marketing": ["marketing.manage"],
    "finance": ["billing.read", "billing.manage", "audit.read"],
    "org_admin": [
        "orgs.read", "orgs.update", "members.read", "members.manage",
        "jobs.create", "jobs.read", "jobs.update",
        "candidates.read", "candidates.update",
        "interviews.create", "interviews.read", "billing.read",
    ],
    "hr": [
        "orgs.read", "jobs.create", "jobs.read", "jobs.update",
        "candidates.read", "candidates.update",
        "interviews.create", "interviews.read",
    ],
    "recruiter": ["orgs.read", "jobs.read", "candidates.read"],
    "hiring_manager": [
        "orgs.read", "jobs.read", "candidates.read",
        "interviews.create", "interviews.read",
    ],
    "government_admin": ["orgs.read", "workforce.aggregates.read"],
    "government_user": ["workforce.aggregates.read"],
}


def seed_catalog(db: Session) -> None:
    """Idempotently insert roles + permissions + role->permission mappings."""
    for code, name, scope, description in ROLES:
        if db.get(Role, code) is None:
            db.add(Role(code=code, name=name, scope=scope, description=description))
    for code, name in PERMISSIONS:
        if db.get(Permission, code) is None:
            db.add(Permission(code=code, name=name))
    db.flush()
    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        for permission_code in permission_codes:
            existing = db.get(RolePermission, (role_code, permission_code))
            if existing is None:
                db.add(
                    RolePermission(
                        role_code=role_code, permission_code=permission_code
                    )
                )
    db.commit()


def role_scope_allows_org_kind(role_scope: str, org_kind: str) -> bool:
    """A membership's role scope must match the organization kind."""
    if role_scope == ROLE_SCOPE_PLATFORM:
        return org_kind == "platform"
    if role_scope == ROLE_SCOPE_GOVERNMENT:
        return org_kind == "government"
    if role_scope == ROLE_SCOPE_ORGANIZATION:
        return org_kind in {"employer", "recruiter"}
    return False
