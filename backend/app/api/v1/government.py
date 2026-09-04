"""/api/v1/government — privacy-preserving workforce intelligence.

No person-id routes. No Work ID browse. No application/interview/document
read. Every handler goes through ``services.government`` which applies
k-threshold suppression before a cell is returned.
"""
from __future__ import annotations

import csv
import io
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.ratelimit import rate_limit_dependency
from app.db.session import get_db
from app.models.identity import User
from app.services import audit as audit_service
from app.services import government as gov

router = APIRouter(prefix="/government", tags=["government"])
query_limit = rate_limit_dependency("government.query")
export_limit = rate_limit_dependency("government.export")


def _filters(
    country: Optional[str] = Query(default=None, max_length=80),
    state_province: Optional[str] = Query(default=None, max_length=80),
    city: Optional[str] = Query(default=None, max_length=80),
    industry: Optional[str] = Query(default=None, max_length=80),
    skill: Optional[str] = Query(default=None, max_length=80),
) -> gov.IntelligenceFilters:
    return gov.parse_filters(
        country=country,
        state_province=state_province,
        city=city,
        industry=industry,
        skill=skill,
    )


def _actor(
    db: Session,
    user: User,
    organization_id: Optional[UUID],
    action: str,
    filters: gov.IntelligenceFilters,
) -> None:
    membership = gov.require_government_reader(db, user.id, organization_id)
    org_id = organization_id or (membership.organization_id if membership else None)
    audit_service.record(
        db,
        actor_id=user.id,
        action=action,
        resource_type="government_intelligence",
        organization_id=org_id,
        metadata={"scope": filters.as_scope()},
    )


@router.get("/overview", dependencies=[Depends(query_limit)])
def overview(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.overview", filters)
    return gov.overview(db, filters)


@router.get("/workforce", dependencies=[Depends(query_limit)])
def workforce(
    group_by: str = Query(default="country", max_length=32),
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.workforce", filters)
    return gov.workforce_distribution(db, filters, group_by)


@router.get("/workforce/geography", dependencies=[Depends(query_limit)])
def workforce_geography(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.geography", filters)
    return gov.geography(db, filters)


@router.get("/workforce/employment", dependencies=[Depends(query_limit)])
def workforce_employment(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.employment", filters)
    return gov.workforce_distribution(db, filters, "employment")


@router.get("/skills", dependencies=[Depends(query_limit)])
def skills(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.skills", filters)
    return gov.skills_intelligence(db, filters)


@router.get("/skills/demand", dependencies=[Depends(query_limit)])
def skills_demand(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.skills.demand", filters)
    body = gov.skills_intelligence(db, filters)
    return {**body, "view": "demand"}


@router.get("/skills/gaps", dependencies=[Depends(query_limit)])
def skills_gaps(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.skills.gaps", filters)
    body = gov.skills_intelligence(db, filters)
    return {**body, "view": "gaps"}


@router.get("/industries", dependencies=[Depends(query_limit)])
def industries(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.industries", filters)
    return gov.industries(db, filters)


@router.get("/opportunities", dependencies=[Depends(query_limit)])
def opportunities(
    group_by: str = Query(default="industry", max_length=32),
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.opportunities", filters)
    return gov.opportunities(db, filters, group_by)


@router.get("/companies", dependencies=[Depends(query_limit)])
def companies(
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.companies", filters)
    return gov.companies(db, filters)


@router.get("/reports/{kind}", dependencies=[Depends(query_limit)])
def reports(
    kind: str,
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
) -> dict:
    _actor(db, user, organization_id, "government.report", filters)
    return gov.report(db, kind, filters)


@router.get("/exports/{kind}", dependencies=[Depends(export_limit)])
def exports(
    kind: str,
    format: str = Query(default="json", alias="format"),
    organization_id: Optional[UUID] = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    filters: gov.IntelligenceFilters = Depends(_filters),
):
    _actor(db, user, organization_id, "government.export", filters)
    if format not in {"json", "csv"}:
        from app.core.errors import InvalidInputError

        raise InvalidInputError("Export format must be json or csv.")
    payload = gov.report(db, kind, filters)
    rows = gov.export_rows(payload)
    if format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["section", "key", "value", "status"])
        writer.writeheader()
        writer.writerows(rows)
        return PlainTextResponse(buf.getvalue(), media_type="text/csv")
    return {
        "kind": kind,
        "format": "json",
        "contains_person_records": False,
        "privacy": payload.get("privacy"),
        "filters": payload.get("filters"),
        "generated_at": payload.get("generated_at"),
        "rows": rows,
    }


@router.get("/settings")
def settings(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    gov.require_government_reader(db, user.id)
    return gov.settings_view(db, user.id)
