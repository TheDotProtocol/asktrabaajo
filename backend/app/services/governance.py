"""Platform governance service (Phase 9).

The governance domain sits ABOVE the product domains:

- Any authenticated user may FILE a report (abuse, fraud, impersonation,
  policy violation, communication dispute, document misuse, recruiter
  misconduct, suspicious activity, platform integrity, ...). The report
  REFERENCES platform objects; it never copies private Work ID data or
  document contents.
- Only platform-scope roles (moderator, governance auditor, super admin)
  may READ the queue, and only with ``reports.*`` permissions. Employers,
  recruiters, candidates and government analysts can never access it.
- Every governance action is audited; internal notes are visible to
  governance roles only.

Least privilege: reading a report gives the moderator the report fields +
audit history + notes — NOT the target's private Work ID sections. Inspecting
private data is a separate, permissioned act (governance report detail never
performs it).
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import (
    InvalidInputError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.timeutil import utc_now_naive
from app.models.enums import (
    PERMISSION_REPORTS_MANAGE,
    PERMISSION_REPORTS_READ,
    REPORT_CATEGORIES,
    REPORT_SEVERITIES,
    REPORT_STATUSES,
    REPORT_STATUS_OPEN,
    REPORT_TARGET_TYPES,
)
from app.models.governance import GovernanceReport, GovernanceReportNote
from app.models.identity import User
from app.models.tenancy import Organization


def _require_platform(db: Session, user_id: uuid.UUID, permission: str) -> None:
    from app.services import authz

    authz.require_platform_permission(db, user_id, permission)


def _report(db: Session, report_id: uuid.UUID) -> GovernanceReport:
    report = db.get(GovernanceReport, report_id)
    if report is None:
        raise NotFoundError("Report not found.")
    return report


# --- filing -------------------------------------------------------------------

def create_report(
    db: Session,
    actor_id: uuid.UUID,
    *,
    target_type: str,
    target_id: str,
    category: str,
    description: str,
    organization_id: Optional[uuid.UUID] = None,
    severity: str = "medium",
    evidence_refs: Optional[list] = None,
) -> GovernanceReport:
    if target_type not in REPORT_TARGET_TYPES:
        raise InvalidInputError(
            f"target_type must be one of {sorted(REPORT_TARGET_TYPES)}."
        )
    if category not in REPORT_CATEGORIES:
        raise InvalidInputError(f"category must be one of {sorted(REPORT_CATEGORIES)}.")
    if severity not in REPORT_SEVERITIES:
        raise InvalidInputError(f"severity must be one of {sorted(REPORT_SEVERITIES)}.")
    if organization_id is not None and db.get(Organization, organization_id) is None:
        raise InvalidInputError("organization_id does not reference an organization.")

    # Evidence references only — {type, id, note}. Contents never accepted.
    normalized_refs = None
    if evidence_refs:
        normalized_refs = []
        for ref in evidence_refs[:10]:
            if not isinstance(ref, dict) or "type" not in ref or "id" not in ref:
                raise InvalidInputError(
                    "evidence_refs entries must be {type, id, note?} references."
                )
            normalized_refs.append(
                {
                    "type": str(ref["type"])[:40],
                    "id": str(ref["id"])[:64],
                    "note": (str(ref.get("note"))[:300] if ref.get("note") else None),
                }
            )

    report = GovernanceReport(
        reporter_user_id=actor_id,
        target_type=target_type,
        target_id=str(target_id)[:64],
        organization_id=organization_id,
        category=category,
        severity=severity,
        status=REPORT_STATUS_OPEN,
        description=description.strip(),
        evidence_refs=normalized_refs,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


# --- queue / detail --------------------------------------------------------------

def list_reports(
    db: Session,
    actor_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    assigned_to: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    page: int = 1,
    page_size: int = 25,
) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    query = select(GovernanceReport)
    if status:
        if status not in REPORT_STATUSES:
            raise InvalidInputError(f"Unknown status '{status}'.")
        query = query.where(GovernanceReport.status == status)
    if severity:
        if severity not in REPORT_SEVERITIES:
            raise InvalidInputError(f"Unknown severity '{severity}'.")
        query = query.where(GovernanceReport.severity == severity)
    if category:
        query = query.where(GovernanceReport.category == category)
    if assigned_to:
        query = query.where(GovernanceReport.assigned_moderator_id == assigned_to)
    if organization_id:
        query = query.where(GovernanceReport.organization_id == organization_id)

    total = len(
        db.scalars(select(func.count()).select_from(query.subquery())).all()
    )
    rows = db.scalars(
        query.order_by(GovernanceReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [report_out(db, r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def report_out(db: Session, report: GovernanceReport, include_notes: bool = False) -> dict:
    org = db.get(Organization, report.organization_id) if report.organization_id else None
    assigned = (
        db.get(User, report.assigned_moderator_id)
        if report.assigned_moderator_id
        else None
    )
    payload = {
        "id": str(report.id),
        "reporter_user_id": str(report.reporter_user_id),
        "target_type": report.target_type,
        "target_id": report.target_id,
        "organization_id": str(report.organization_id) if report.organization_id else None,
        "organization_name": org.name if org else None,
        "category": report.category,
        "severity": report.severity,
        "status": report.status,
        "description": report.description,
        "evidence_refs": report.evidence_refs or [],
        "assigned_moderator_id": (
            str(report.assigned_moderator_id) if report.assigned_moderator_id else None
        ),
        "assigned_moderator_name": assigned.full_name if assigned else None,
        "resolution": report.resolution,
        "resolved_at": report.resolved_at,
        "reopened_count": report.reopened_count,
        "created_at": report.created_at,
        "updated_at": report.updated_at,
    }
    if include_notes:
        notes = db.scalars(
            select(GovernanceReportNote)
            .where(GovernanceReportNote.report_id == report.id)
            .order_by(GovernanceReportNote.created_at.asc())
        ).all()
        payload["notes"] = [
            {
                "id": str(n.id),
                "author_user_id": str(n.author_user_id),
                "body": n.body,
                "created_at": n.created_at,
            }
            for n in notes
        ]
    return payload


def get_report(db: Session, actor_id: uuid.UUID, report_id: uuid.UUID) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    report = _report(db, report_id)
    return report_out(db, report, include_notes=True)


def governance_dashboard(db: Session, actor_id: uuid.UUID) -> dict:
    _require_platform(db, actor_id, PERMISSION_REPORTS_READ)
    rows = db.execute(
        select(GovernanceReport.status, func.count())
        .group_by(GovernanceReport.status)
    ).all()
    severity_rows = db.execute(
        select(GovernanceReport.severity, func.count())
        .group_by(GovernanceReport.severity)
    ).all()
    total = len(
        db.scalars(select(func.count()).select_from(GovernanceReport)).all()
    )
    return {
        "total": total,
        "by_status": {status: count for status, count in rows},
        "by_severity": {severity: count for severity, count in severity_rows},
        "open": sum(count for status, count in rows if status in {
            "open", "in_review", "assigned",
        }),
    }


# --- moderation actions -----------------------------------------------------------

def update_status(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    status: str,
) -> GovernanceReport:
    _require_platform(db, actor_id, PERMISSION_REPORTS_MANAGE)
    if status not in REPORT_STATUSES:
        raise InvalidInputError(f"Unknown status '{status}'.")
    report = _report(db, report_id)
    if report.status == "resolved" and status != "closed":
        raise InvalidInputError("Resolved reports must be reopened before rework.")
    report.status = status
    if status == "assigned" and report.assigned_moderator_id is None:
        report.assigned_moderator_id = actor_id
    db.commit()
    db.refresh(report)
    return report


def assign_report(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    moderator_user_id: Optional[uuid.UUID] = None,
) -> GovernanceReport:
    _require_platform(db, actor_id, "reports.assign")
    report = _report(db, report_id)
    if moderator_user_id is None:
        moderator_user_id = actor_id
    else:
        # The assignee must be a platform governance actor (no arbitrary user).
        _require_platform(db, moderator_user_id, "reports.read")
    report.assigned_moderator_id = moderator_user_id
    if report.status in {"open", "in_review"}:
        report.status = "assigned"
    db.commit()
    db.refresh(report)
    return report


def add_note(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    body: str,
) -> GovernanceReportNote:
    _require_platform(db, actor_id, PERMISSION_REPORTS_MANAGE)
    report = _report(db, report_id)
    if report.status == "closed":
        raise InvalidInputError("Closed reports cannot be annotated; reopen first.")
    note = GovernanceReportNote(report_id=report.id, author_user_id=actor_id, body=body.strip())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def resolve_report(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
    resolution: str,
) -> GovernanceReport:
    _require_platform(db, actor_id, "reports.resolve")
    report = _report(db, report_id)
    if report.status in {"resolved", "closed"}:
        raise InvalidInputError("This report is already resolved/closed.")
    report.status = "resolved"
    report.resolution = resolution.strip()
    report.resolved_at = utc_now_naive()
    report.resolved_by = actor_id
    db.commit()
    db.refresh(report)
    return report


def reopen_report(
    db: Session,
    actor_id: uuid.UUID,
    report_id: uuid.UUID,
) -> GovernanceReport:
    _require_platform(db, actor_id, "reports.resolve")
    report = _report(db, report_id)
    if report.status not in {"resolved", "closed"}:
        raise InvalidInputError("Only resolved/closed reports can be reopened.")
    report.status = "in_review"
    report.reopened_count += 1
    report.resolved_at = None
    report.resolved_by = None
    db.commit()
    db.refresh(report)
    return report