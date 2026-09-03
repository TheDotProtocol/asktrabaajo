"""Canonical model set — import every model module so metadata is complete."""
from app.models import audit, documents, identity, tenancy, work
from app.models.audit import AuditLogEntry
from app.models.documents import DocumentAccessGrant, PersonDocument
from app.models.identity import PersonProfile, RefreshToken, TimestampMixin, User
from app.models.tenancy import (
    ROLE_SUPER_ADMIN,
    Membership,
    Organization,
    Permission,
    Role,
    RolePermission,
)
from app.models.work import (
    Credential,
    Education,
    Employment,
    Skill,
    UserSkill,
    WorkExperience,
)

__all__ = [
    "AuditLogEntry",
    "Credential",
    "DocumentAccessGrant",
    "Education",
    "Employment",
    "Membership",
    "Organization",
    "Permission",
    "PersonDocument",
    "PersonProfile",
    "RefreshToken",
    "Role",
    "RolePermission",
    "Skill",
    "TimestampMixin",
    "User",
    "UserSkill",
    "WorkExperience",
    "ROLE_SUPER_ADMIN",
]
