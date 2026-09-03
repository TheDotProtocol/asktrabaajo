"""/api/v1/governance — the Platform Governance API (Phase 9).

Boundaries enforced here:

- FILING a report is open to any authenticated user (candidate, company,
  recruiter, government analyst...). The report references platform objects;
  it never carries private Work ID data or document contents.
- READING/MODIFYING the queue requires a PLATFORM-scope role with the
  specific ``reports.*`` permission. Employer, recruiter, candidate and
  government memberships can never satisfy it (``has_platform_permission``
  only counts memberships inside platform-kind organizations).
- Report detail returns the report + internal notes + audit history — never
  the target's private Work ID sections (least privilege).
- Every governance action is audited.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.audit import AuditLogEntry
from app.models.enums import (
    PERMISSION_REPORTS_READ,
    REPORT_CATEGORIES,
    REPORT_SEVERITIES,
    REPORT_STATUSES,
)
from app.models.identity import User
from app.schemas.common import MessageResponse
from app.schemas.governance import (
    GovernanceDashboardOut,
    ReportAssign,
    ReportCreate,
    ReportListOut,
    ReportNoteCreate,
    ReportOut,
    ReportResolve,
    ReportStatusUpdate,
)
from app.services import audit as audit_service
from app.services import governance as governance_service
from app.services import notifications as notifications_service

router = APIRouter(prefix="/governance", tags=["governance"])


@router.post("/reports", response_model=ReportOut, status_code=201)
def file_report(
    body: ReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Any authenticated user may file a report (references only)."""
    report = governance_service.create_report(
        db,
        user.id,
        target_type=body.target_type,
        target_id=body.target_id,
        category=body.category,
        description=body.description,
        organization_id=body.organization_id,
        severity=body.severity,
        evidence_refs=body.evidence_refs,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.created",
        resource_type="governance_report",
        resource_id=report.id,
        organization_id=report.organization_id,
        metadata={
            "target_type": report.target_type,
            "category": report.category,
            "severity": report.severity,
        },
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.get("/reports", response_model=ReportListOut)
def list_reports(
    status: Optional[str] = Query(None, max_length=20),
    severity: Optional[str] = Query(None, max_length=16),
    category: Optional[str] = Query(None, max_length=40),
    assigned_to: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Platform governance queue (moderator/super-admin only)."""
    return governance_service.list_reports(
        db,
        user.id,
        status=status,
        severity=severity,
        category=category,
        assigned_to=assigned_to,
        organization_id=organization_id,
        page=page,
        page_size=page_size,
    )


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Report detail: fields + internal notes + audit history. Never the
    target's private Work ID sections (least privilege)."""
    payload = governance_service.get_report(db, user.id, report_id)
    audit_rows = db.scalars(
        select(AuditLogEntry)
        .where(
            AuditLogEntry.resource_type == "governance_report",
            AuditLogEntry.resource_id == str(report_id),
        )
        .order_by(AuditLogEntry.created_at.desc())
        .limit(50)
    ).all()
    payload["audit"] = [
        {
            "action": row.action,
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "result": row.result,
            "created_at": row.created_at,
            "payload": row.payload or {},
        }
        for row in audit_rows
    ]
    return payload


@router.patch("/reports/{report_id}/status", response_model=ReportOut)
def update_report_status(
    report_id: uuid.UUID,
    body: ReportStatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.update_status(db, user.id, report_id, body.status)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.status_changed",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"to_status": body.status},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/assign", response_model=ReportOut)
def assign_report(
    report_id: uuid.UUID,
    body: ReportAssign,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.assign_report(
        db, user.id, report_id, moderator_user_id=body.moderator_user_id
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.assigned",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"to_user_id": str(report.assigned_moderator_id)},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/notes", response_model=dict, status_code=201)
def add_report_note(
    report_id: uuid.UUID,
    body: ReportNoteCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    note = governance_service.add_note(db, user.id, report_id, body.body)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.note_added",
        resource_type="governance_report",
        resource_id=report_id,
        metadata={"note_id": str(note.id)},
    )
    db.commit()
    return {
        "id": str(note.id),
        "report_id": str(note.report_id),
        "author_user_id": str(note.author_user_id),
        "body": note.body,
        "created_at": note.created_at,
    }


@router.post("/reports/{report_id}/resolve", response_model=ReportOut)
def resolve_report(
    report_id: uuid.UUID,
    body: ReportResolve,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.resolve_report(db, user.id, report_id, body.resolution)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.resolved",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"resolution_present": bool(body.resolution)},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.post("/reports/{report_id}/reopen", response_model=ReportOut)
def reopen_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    report = governance_service.reopen_report(db, user.id, report_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="governance.report.reopened",
        resource_type="governance_report",
        resource_id=report.id,
        metadata={"reopened_count": report.reopened_count},
    )
    db.commit()
    return governance_service.report_out(db, report)


@router.get("/dashboard", response_model=GovernanceDashboardOut)
def governance_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return governance_service.governance_dashboard(db, user.id)