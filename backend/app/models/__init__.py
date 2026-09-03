"""Canonical model set — import every model module so metadata is complete."""
from app.models import audit, career, documents, identity, privacy, tenancy, work
from app.models.career import (
    ApplicationEvent,
    CareerGoal,
    CareerMilestone,
    Interview,
    JobApplication,
    Offer,
    Opportunity,
    OpportunityInteraction,
    UserNotification,
    WorkDnaAnswer,
    WorkDnaProfile,
)
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
    "ApplicationEvent",
    "AuditLogEntry",
    "CareerGoal",
    "CareerMilestone",
    "Consent",
    "Credential",
    "DocumentAccessGrant",
    "Education",
    "EmailVerificationToken",
    "Employment",
    "Interview",
    "JobApplication",
    "Membership",
    "Offer",
    "Opportunity",
    "OpportunityInteraction",
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
    "UserNotification",
    "UserSkill",
    "WorkDnaAnswer",
    "WorkDnaProfile",
    "WorkExperience",
    "ROLE_SUPER_ADMIN",
]
