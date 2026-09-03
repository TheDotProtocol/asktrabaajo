"""/api/v1/company — the Company / HR / Recruiter Employment OS API.

Every route is organization-scoped: the caller must hold a membership in the
organization AND the specific permission for the operation (RBAC catalog).
Company A can never reach Company B rows — permissions are always checked
against the requested ``organization_id`` and every query is tenant-scoped.

The candidate lifecycle is shared with the jobseeker Career OS: employer
decisions go through the same application state machine, offers are created
here and decided by the candidate there, and document access always requires
candidate authorization (progressive disclosure).
"""
from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_org_permission
from app.core.errors import InvalidInputError, NotFoundError
from app.db.session import get_db
from app.models.career import Interview, JobApplication, Offer, Opportunity
from app.models.company import CompanyProfile, InterviewScorecard
from app.models.enums import (
    INTERVIEW_STATUS_SCHEDULED,
    JOB_STATUSES,
    SCORECARD_RECOMMENDATIONS,
)
from app.models.identity import User
from app.models.tenancy import Organization
from app.schemas.common import MessageResponse
from app.schemas.company import (
    AnalyticsOut,
    ApplicationReviewOut,
    CandidateSummaryOut,
    CompanyDashboardOut,
    CompanyProfileOut,
    CompanyProfileUpdate,
    DecisionRequest,
    DocumentRequestCreate,
    DocumentRequestOut,
    InterviewCreate,
    JobCreate,
    JobOut,
    JobUpdate,
    OfferCreate,
    ScorecardCreate,
    ScorecardOut,
)
from app.services import audit as audit_service
from app.services import authz
from app.services import company_os as employer
from app.services import notifications as notifications_service
from app.services import tenancy
from app.services.company_os import (
    REVIEW_STATUSES,
    _candidate_person,
    _candidate_user_id,
    candidate_summary,
    create_interview,
    create_job,
    create_offer,
    decision,
    hiring_analytics,
    list_org_applications,
    list_org_jobs,
    mark_interview_completed,
    pause_job,
    publish_job,
    request_document,
    close_job,
)
from app.services.auth_service import get_person_for_user

router = APIRouter(prefix="/company", tags=["company"])


# --- helpers -----------------------------------------------------------------


def _org(db: Session, organization_id: uuid.UUID) -> Organization:
    org = tenancy.get_organization(db, organization_id)
    return org


def _job_dict(job, applications_count: int = 0) -> dict:
    data = {
        "id": str(job.id),
        "organization_id": str(job.organization_id),
        "opportunity_id": str(job.opportunity_id) if job.opportunity_id else None,
        "title": job.title,
        "slug": job.slug,
        "department": job.department,
        "summary": job.summary,
        "description": job.description,
        "requirements": job.requirements,
        "skills_required": job.skills_required,
        "preferred_skills": job.preferred_skills,
        "experience_level": job.experience_level,
        "location": job.location,
        "country": job.country,
        "city": job.city,
        "remote_eligible": job.remote_eligible,
        "work_mode": job.work_mode,
        "employment_type": job.employment_type,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "seniority": job.seniority,
        "industry": job.industry,
        "openings_count": job.openings_count,
        "application_deadline": (
            job.application_deadline.isoformat() if job.application_deadline else None
        ),
        "screening_questions": job.screening_questions,
        "status": job.status,
        "published_at": job.published_at,
        "applications_count": applications_count,
    }
    return data


def _count_applications_for_job(db: Session, opportunity_id) -> int:
    if not opportunity_id:
        return 0
    return len(
        db.scalars(
            select(JobApplication.id).where(
                JobApplication.opportunity_id == opportunity_id
            )
        ).all()
    )


# --- Company profile -----------------------------------------------------------


@router.get("/{organization_id}/profile", response_model=CompanyProfileOut)
def get_company_profile(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyProfile:
    require_org_permission(db, user, "orgs.read", organization_id)
    org = _org(db, organization_id)
    profile = db.get(CompanyProfile, org.id)
    if profile is None:
        profile = CompanyProfile(
            organization_id=org.id,
            display_name=org.name,
            verification_status="unverified",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.patch("/{organization_id}/profile", response_model=CompanyProfileOut)
def update_company_profile(
    organization_id: uuid.UUID,
    body: CompanyProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyProfile:
    require_org_permission(db, user, "company.manage", organization_id)
    profile = get_company_profile(organization_id, user, db)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    audit_service.record(
        db,
        actor_id=user.id,
        action="company.profile.updated",
        resource_type="company_profile",
        resource_id=organization_id,
        organization_id=organization_id,
    )
    db.commit()
    return profile


# --- Dashboard ----------------------------------------------------------------

@router.get("/{organization_id}/dashboard", response_model=CompanyDashboardOut)
def company_dashboard(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CompanyDashboardOut:
    require_org_permission(db, user, "jobs.view", organization_id)
    membership = authz.require_membership(db, user.id, organization_id)
    org = _org(db, organization_id)
    profile = db.get(CompanyProfile, org.id)

    open_jobs = [j for j in list_org_jobs(db, org.id, status="published")]
    apps = list_org_applications(db, org.id)
    by_status: dict = {}
    for app in apps:
        by_status[app.status] = by_status.get(app.status, 0) + 1
    needs_review = sum(by_status.get(s, 0) for s in REVIEW_STATUSES)

    app_ids = [a.id for a in apps]
    interviews = (
        db.scalars(
            select(Interview).where(
                Interview.application_id.in_(app_ids or [uuid.uuid4()]),
                Interview.status == INTERVIEW_STATUS_SCHEDULED,
            )
        ).all()
        if app_ids
        else []
    )
    from app.core.timeutil import utc_now_naive
    from datetime import timedelta

    now = utc_now_naive()
    today = [i for i in interviews if abs((i.scheduled_at - now).days) == 0]
    upcoming = [i for i in interviews if i.scheduled_at > now]

    offer_app_ids = app_ids
    pending_offers = (
        db.scalars(
            select(Offer).where(
                Offer.application_id.in_(offer_app_ids or [uuid.uuid4()]),
                Offer.status.in_(["draft", "sent"]),
            )
        ).all()
        if offer_app_ids
        else []
    )
    accepted_offers = (
        db.scalars(
            select(Offer).where(
                Offer.application_id.in_(offer_app_ids or [uuid.uuid4()]),
                Offer.status == "accepted",
            )
        ).all()
        if offer_app_ids
        else []
    )

    recent = apps[:5]
    permissions = sorted(
        authz.permission_codes_for_org(db, user.id, organization_id)
    )
    return CompanyDashboardOut(
        organization={
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "kind": org.kind,
        },
        profile=CompanyProfileOut.model_validate(profile) if profile else None,
        open_jobs=len(open_jobs),
        applications_total=len(apps),
        needs_review=needs_review,
        interviews_today=len(today),
        interviews_upcoming=len(upcoming),
        offers_pending=len(pending_offers),
        offers_accepted=len(accepted_offers),
        recent_applications=[
            {
                "id": str(a.id),
                "status": a.status,
                "job_title": (
                    a.opportunity.title if a.opportunity else "Opportunity"
                ),
                "applied_at": a.applied_at,
                "candidate_name": (
                    _candidate_display_name_safe(db, a)
                ),
            }
            for a in recent
        ],
        my_role=membership.role_code,
        permissions=permissions,
    )


def _candidate_display_name_safe(db: Session, application: JobApplication) -> str:
    person = get_person_for_user(db, _candidate_user_id(db, application))
    if person is None:
        return "Candidate"
    user = db.get(User, person.user_id)
    if user and person.preferred_name:
        return person.preferred_name
    return user.full_name if user else "Candidate"


# --- Jobs ----------------------------------------------------------------------


@router.get("/{organization_id}/jobs", response_model=list[JobOut])
def list_jobs(
    organization_id: uuid.UUID,
    status: Optional[str] = Query(None, max_length=20),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, "jobs.view", organization_id)
    org = _org(db, organization_id)
    jobs = list_org_jobs(db, org.id, status=status)
    return [
        JobOut.model_validate(
            _job_dict(job, _count_applications_for_job(db, job.opportunity_id))
        )
        for job in jobs
    ]


@router.get("/{organization_id}/jobs/{job_id}", response_model=JobOut)
def get_job(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "jobs.view", organization_id)
    org = _org(db, organization_id)
    from app.services.company_os import _job_owned

    job = _job_owned(db, org.id, job_id)
    return JobOut.model_validate(
        _job_dict(job, _count_applications_for_job(db, job.opportunity_id))
    )


@router.post("/{organization_id}/jobs", response_model=JobOut, status_code=201)
def create_job_endpoint(
    organization_id: uuid.UUID,
    body: JobCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "jobs.create", organization_id)
    org = _org(db, organization_id)
    job = create_job(
        db,
        org.id,
        user.id,
        title=body.title,
        summary=body.summary,
        description=body.description,
        department=body.department,
        requirements=body.requirements,
        skills_required=body.skills_required,
        preferred_skills=body.preferred_skills,
        experience_level=body.experience_level,
        location=body.location,
        country=body.country,
        city=body.city,
        remote_eligible=body.remote_eligible,
        work_mode=body.work_mode,
        employment_type=body.employment_type,
        salary_min=body.salary_min,
        salary_max=body.salary_max,
        salary_currency=body.salary_currency,
        seniority=body.seniority,
        industry=body.industry,
        openings_count=body.openings_count,
        application_deadline=body.application_deadline,
        screening_questions=body.screening_questions,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="job.created",
        resource_type="job_posting",
        resource_id=job.id,
        organization_id=org.id,
        metadata={"title": job.title, "status": job.status},
    )
    db.commit()
    return JobOut.model_validate(_job_dict(job))


@router.patch("/{organization_id}/jobs/{job_id}", response_model=JobOut)
def update_job_endpoint(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    body: JobUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "jobs.update", organization_id)
    org = _org(db, organization_id)
    job = employer.update_job(
        db, org.id, job_id, user.id, body.model_dump(exclude_unset=True)
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="job.updated",
        resource_type="job_posting",
        resource_id=job.id,
        organization_id=org.id,
    )
    db.commit()
    return JobOut.model_validate(_job_dict(job, _count_applications_for_job(db, job.opportunity_id)))


@router.post("/{organization_id}/jobs/{job_id}/publish", response_model=JobOut)
def publish_job_endpoint(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "jobs.publish", organization_id)
    org = _org(db, organization_id)
    job = publish_job(db, org.id, job_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="job.published",
        resource_type="job_posting",
        resource_id=job.id,
        organization_id=org.id,
        metadata={"opportunity_id": str(job.opportunity_id) if job.opportunity_id else None},
    )
    db.commit()
    return JobOut.model_validate(_job_dict(job, _count_applications_for_job(db, job.opportunity_id)))


@router.post("/{organization_id}/jobs/{job_id}/pause", response_model=JobOut)
def pause_job_endpoint(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "jobs.publish", organization_id)
    org = _org(db, organization_id)
    job = pause_job(db, org.id, job_id)
    db.commit()
    return JobOut.model_validate(_job_dict(job, _count_applications_for_job(db, job.opportunity_id)))


@router.post("/{organization_id}/jobs/{job_id}/close", response_model=JobOut)
def close_job_endpoint(
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "jobs.publish", organization_id)
    org = _org(db, organization_id)
    job = close_job(db, org.id, job_id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="job.closed",
        resource_type="job_posting",
        resource_id=job.id,
        organization_id=org.id,
    )
    db.commit()
    return JobOut.model_validate(_job_dict(job, _count_applications_for_job(db, job.opportunity_id)))


# --- Pipeline -----------------------------------------------------------------


@router.get("/{organization_id}/applications", response_model=list)
def list_company_applications(
    organization_id: uuid.UUID,
    job_id: Optional[uuid.UUID] = None,
    status: Optional[str] = Query(None, max_length=32),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, "applications.view", organization_id)
    org = _org(db, organization_id)
    apps = list_org_applications(db, org.id, job_id=job_id, status=status)
    result = []
    for app in apps:
        person = get_person_for_user(db, _candidate_user_id(db, app))
        user_row = db.get(User, person.user_id) if person else None
        result.append(
            {
                "id": str(app.id),
                "status": app.status,
                "job_id": str(app.job_id) if app.job_id else None,
                "opportunity_id": str(app.opportunity_id) if app.opportunity_id else None,
                "job_title": app.opportunity.title if app.opportunity else None,
                "candidate_name": (
                    (person.preferred_name or user_row.full_name) if person and user_row else "Candidate"
                ),
                "applied_at": app.applied_at,
                "last_activity_at": app.last_activity_at,
            }
        )
    return result


@router.get("/{organization_id}/applications/{application_id}", response_model=ApplicationReviewOut)
def review_application(
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ApplicationReviewOut:
    require_org_permission(db, user, "applications.view", organization_id)
    org = _org(db, organization_id)
    app = employer._application_owned(db, org.id, application_id, actor_id=user.id)
    candidate = candidate_summary(db, org.id, app, user.id)
    interview = db.scalar(
        select(Interview)
        .where(Interview.application_id == app.id)
        .order_by(Interview.created_at.desc())
        .limit(1)
    )
    offer = db.scalar(
        select(Offer).where(Offer.application_id == app.id).limit(1)
    )
    return ApplicationReviewOut(
        application={
            "id": str(app.id),
            "status": app.status,
            "opportunity_id": str(app.opportunity_id) if app.opportunity_id else None,
            "job_id": str(app.job_id) if app.job_id else None,
            "cover_note": app.cover_note,
            "applied_at": app.applied_at,
            "last_activity_at": app.last_activity_at,
        },
        job={
            "id": str(app.job_id) if app.job_id else None,
            "title": app.opportunity.title if app.opportunity else None,
        },
        candidate=CandidateSummaryOut(**candidate),
        interview=(
            {
                "id": str(interview.id),
                "scheduled_at": interview.scheduled_at,
                "status": interview.status,
                "mode": interview.mode,
                "interviewer_name": interview.interviewer_name,
            }
            if interview
            else None
        ),
        offer=(
            {
                "id": str(offer.id),
                "status": offer.status,
                "salary_amount": offer.salary_amount,
                "salary_currency": offer.salary_currency,
            }
            if offer
            else None
        ),
    )


@router.post("/{organization_id}/applications/{application_id}/decision", response_model=dict)
def application_decision(
    organization_id: uuid.UUID,
    application_id: uuid.UUID,
    body: DecisionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "applications.manage", organization_id)
    org = _org(db, organization_id)
    app = decision(
        db, org.id, application_id, user.id, action=body.action, note=body.note
    )
    # ensure non-members of the owning org are 403'd at the membership layer too
    audit_service.record(
        db,
        actor_id=user.id,
        action=f"application.decision.{body.action}",
        resource_type="job_application",
        resource_id=app.id,
        organization_id=org.id,
        metadata={"to_status": app.status, "note": body.note},
    )
    # Notify the candidate.
    candidate_user_id = _candidate_user_id(db, app)
    if candidate_user_id:
        notifications_service.notify(
            db,
            candidate_user_id,
            "Your application was updated",
            f"Your application moved to '{app.status}'.",
            kind="application",
        )
    db.commit()
    return {"application_id": str(app.id), "status": app.status, "action": body.action}


# --- Interviews ----------------------------------------------------------------


@router.post("/{organization_id}/interviews", response_model=dict, status_code=201)
def schedule_interview(
    organization_id: uuid.UUID,
    body: InterviewCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "interviews.create", organization_id)
    org = _org(db, organization_id)
    interview = create_interview(
        db,
        org.id,
        body.application_id,
        user.id,
        scheduled_at=body.scheduled_at,
        duration_minutes=body.duration_minutes,
        mode=body.mode,
        interviewer_name=body.interviewer_name,
        meeting_link=body.meeting_link,
        notes=body.notes,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="interview.scheduled",
        resource_type="interview",
        resource_id=interview.id,
        organization_id=org.id,
    )
    db.commit()
    return {
        "id": str(interview.id),
        "application_id": str(interview.application_id),
        "scheduled_at": interview.scheduled_at,
        "status": interview.status,
    }


@router.get("/{organization_id}/interviews", response_model=list)
def list_company_interviews(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, "interviews.read", organization_id)
    org = _org(db, organization_id)
    opp_ids = employer.org_opportunity_ids(db, org.id)
    app_ids = (
        db.scalars(
            select(JobApplication.id).where(
                JobApplication.opportunity_id.in_(opp_ids or [uuid.uuid4()])
            )
        ).all()
    )
    if not app_ids:
        return []
    interviews = db.scalars(
        select(Interview)
        .where(Interview.application_id.in_(app_ids))
        .order_by(Interview.scheduled_at.desc())
    ).all()
    return [
        {
            "id": str(i.id),
            "application_id": str(i.application_id),
            "scheduled_at": i.scheduled_at,
            "status": i.status,
            "mode": i.mode,
            "interviewer_name": i.interviewer_name,
            "duration_minutes": i.duration_minutes,
            "reschedule_count": i.reschedule_count,
        }
        for i in interviews
    ]


@router.post("/{organization_id}/interviews/{interview_id}/complete", response_model=dict)
def complete_interview(
    organization_id: uuid.UUID,
    interview_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "interviews.manage", organization_id)
    org = _org(db, organization_id)
    interview = mark_interview_completed(db, org.id, interview_id, actor_id=user.id)
    db.commit()
    return {"id": str(interview.id), "status": interview.status}


@router.post("/{organization_id}/interviews/{interview_id}/confirm-reschedule", response_model=dict)
def confirm_reschedule_endpoint(
    organization_id: uuid.UUID,
    interview_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "interviews.manage", organization_id)
    org = _org(db, organization_id)
    interview = employer.confirm_reschedule(db, org.id, interview_id, actor_id=user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="interview.reschedule.confirmed",
        resource_type="interview",
        resource_id=interview.id,
        organization_id=org.id,
    )
    db.commit()
    return {"id": str(interview.id), "status": interview.status}


@router.post("/{organization_id}/interviews/{interview_id}/scorecards", response_model=ScorecardOut, status_code=201)
def add_scorecard(
    organization_id: uuid.UUID,
    interview_id: uuid.UUID,
    body: ScorecardCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InterviewScorecard:
    require_org_permission(db, user, "interviews.manage", organization_id)
    org = _org(db, organization_id)
    interview = employer._owned_interview(db, org.id, interview_id, actor_id=user.id)
    if body.recommendation and body.recommendation not in SCORECARD_RECOMMENDATIONS:
        raise InvalidInputError("recommendation must be advance/hold/reject.")
    scorecard = InterviewScorecard(
        interview_id=interview.id,
        interviewer_user_id=user.id,
        criteria=body.criteria,
        strengths=body.strengths,
        concerns=body.concerns,
        recommendation=body.recommendation,
        notes=body.notes,
    )
    db.add(scorecard)
    db.commit()
    db.refresh(scorecard)
    audit_service.record(
        db,
        actor_id=user.id,
        action="interview.scorecard.created",
        resource_type="interview_scorecard",
        resource_id=scorecard.id,
        organization_id=org.id,
    )
    db.commit()
    return scorecard


# --- Offers ---------------------------------------------------------------------


@router.post("/{organization_id}/offers", response_model=dict, status_code=201)
def create_offer_endpoint(
    organization_id: uuid.UUID,
    body: OfferCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "offers.create", organization_id)
    org = _org(db, organization_id)
    offer = create_offer(
        db,
        org.id,
        body.application_id,
        user.id,
        salary_amount=body.salary_amount,
        salary_currency=body.salary_currency,
        equity=body.equity,
        benefits_summary=body.benefits_summary,
        start_date=body.start_date,
        location=body.location,
        terms_summary=body.terms_summary,
        expires_days=body.expires_days,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="offer.created",
        resource_type="offer",
        resource_id=offer.id,
        organization_id=org.id,
    )
    db.commit()
    return {
        "id": str(offer.id),
        "application_id": str(offer.application_id),
        "status": offer.status,
        "salary_amount": offer.salary_amount,
        "salary_currency": offer.salary_currency,
    }


@router.get("/{organization_id}/offers", response_model=list)
def list_company_offers(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, "offers.manage", organization_id)
    org = _org(db, organization_id)
    opp_ids = employer.org_opportunity_ids(db, org.id)
    app_ids = (
        db.scalars(
            select(JobApplication.id).where(
                JobApplication.opportunity_id.in_(opp_ids or [uuid.uuid4()])
            )
        ).all()
    )
    if not app_ids:
        return []
    offers = db.scalars(
        select(Offer).where(Offer.application_id.in_(app_ids))
    ).all()
    return [
        {
            "id": str(o.id),
            "application_id": str(o.application_id),
            "status": o.status,
            "salary_amount": o.salary_amount,
            "salary_currency": o.salary_currency,
            "responded_at": o.responded_at,
        }
        for o in offers
    ]


@router.post("/{organization_id}/offers/{offer_id}/send", response_model=dict)
def send_offer_endpoint(
    organization_id: uuid.UUID,
    offer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "offers.manage", organization_id)
    org = _org(db, organization_id)
    offer = employer.send_offer(db, org.id, offer_id, user.id)
    audit_service.record(
        db,
        actor_id=user.id,
        action="offer.sent",
        resource_type="offer",
        resource_id=offer.id,
        organization_id=org.id,
    )
    db.commit()
    return {"id": str(offer.id), "status": offer.status}


@router.post("/{organization_id}/offers/{offer_id}/withdraw", response_model=dict)
def withdraw_offer_endpoint(
    organization_id: uuid.UUID,
    offer_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "offers.manage", organization_id)
    org = _org(db, organization_id)
    offer = employer.withdraw_offer(db, org.id, offer_id, user.id)
    db.commit()
    return {"id": str(offer.id), "status": offer.status}


# --- Document requests ---------------------------------------------------------


@router.post("/{organization_id}/document-requests", response_model=DocumentRequestOut, status_code=201)
def create_document_request(
    organization_id: uuid.UUID,
    body: DocumentRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "applications.manage", organization_id)
    org = _org(db, organization_id)
    request = request_document(
        db, org.id, body.application_id, user.id,
        document_type=body.document_type, purpose=body.purpose,
    )
    audit_service.record(
        db,
        actor_id=user.id,
        action="document.requested",
        resource_type="document_request",
        resource_id=request.id,
        organization_id=org.id,
        metadata={"document_type": body.document_type},
    )
    db.commit()
    return request


@router.get("/{organization_id}/document-requests", response_model=list[DocumentRequestOut])
def list_document_requests(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list:
    require_org_permission(db, user, "applications.view", organization_id)
    org = _org(db, organization_id)
    app_ids = [
        a.id for a in list_org_applications(db, org.id)
    ]
    if not app_ids:
        return []
    from app.models.company import DocumentRequest

    return db.scalars(
        select(DocumentRequest)
        .where(DocumentRequest.organization_id == org.id)
        .order_by(DocumentRequest.created_at.desc())
    ).all()


# --- Analytics ------------------------------------------------------------------


@router.get("/{organization_id}/analytics", response_model=AnalyticsOut)
def company_analytics(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_org_permission(db, user, "analytics.view", organization_id)
    org = _org(db, organization_id)
    return AnalyticsOut(**hiring_analytics(db, org.id))
