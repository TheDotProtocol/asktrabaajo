"""Canonical model set — import every model module so metadata is complete."""
from app.models import audit, documents, identity, privacy, tenancy, work
from app.models.audit import AuditLogEntry
from app.models.documents import DocumentAccessGrant, PersonDocument
from app.models.identity import (
    EmailVerificationToken,
    PasswordResetToken,
    PersonProfile,
    RefreshToken,
    TimestampMixin,
    User,
)
from app.models.privacy import Consent, PersonVisibilitySetting
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
    "Consent",
    "Credential",
    "DocumentAccessGrant",
    "Education",
    "EmailVerificationToken",
    "Employment",
    "Membership",
    "Organization",
    "PasswordResetToken",
    "Permission",
    "PersonDocument",
    "PersonProfile",
    "PersonVisibilitySetting",
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
