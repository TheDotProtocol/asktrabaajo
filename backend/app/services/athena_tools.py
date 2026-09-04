"""Athena tool registry (Phase 14).

Every tool declares its permission, allowed modes, risk, and data scope
up front. The model may only select from this registry; authorization is
enforced in application code (never by the model). Handlers call the same
canonical services the REST API uses — Athena cannot reach the database
or filesystem directly, and unknown tool names are always refused.

Tools map 1:1 to existing canonical functionality; nothing here invents
new business behavior.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError
from app.models.career import (
    CareerGoal,
    Interview,
    JobApplication,
    Offer,
    Opportunity,
)
from app.models.enums import (
    ATHENA_MODE_EMPLOYER,
    ATHENA_MODE_JOBSEEKER,
    ATHENA_MODE_RECRUITER,
    ATHENA_RISK_HIGH_RISK_WRITE,
    ATHENA_RISK_LOW_RISK_WRITE,
    ATHENA_RISK_READ_ONLY,
    CREDENTIAL_STATUS_VERIFIED,
    JOB_STATUS_PUBLISHED,
    OPPORTUNITY_SOURCE_PLATFORM,
)
from app.models.identity import PersonProfile, User
from app.models.work import Credential, Education, Skill, UserSkill, WorkExperience
from app.services import applications as applications_service
from app.services import communications as communications_service
from app.services import matching as matching_service
from app.services import outreach as outreach_service
from app.services import talent as talent_service
from app.services.company_os import candidate_summary, list_org_applications, list_org_jobs

Handler = Callable[[Session, User, "AthenaSession", uuid.UUID, Dict], Dict]


# --- Tool input schemas (validated; also generate the provider JSON schema) ---
class EmptyIn(BaseModel):
    """Tools with no arguments."""

    pass


class OpportunityIdsIn(BaseModel):
    opportunity_ids: List[uuid.UUID] = Field(min_length=2, max_length=5)


class OpportunityIn(BaseModel):
    opportunity_id: uuid.UUID


class ApplicationIn(BaseModel):
    application_id: uuid.UUID


class ConversationIn(BaseModel):
    conversation_id: uuid.UUID


class SaveOpportunityIn(BaseModel):
    opportunity_id: uuid.UUID


class ApplyIn(BaseModel):
    opportunity_id: uuid.UUID
    cover_note: Optional[str] = Field(default=None, max_length=2000)


class SearchOpportunitiesIn(BaseModel):
    q: Optional[str] = Field(default=None, max_length=200)
    skills: Optional[List[str]] = Field(default=None, max_length=10)
    location: Optional[str] = Field(default=None, max_length=120)
    page: int = Field(default=1, ge=1, le=100)


class SearchTalentIn(BaseModel):
    q: Optional[str] = Field(default=None, max_length=200)
    skills: Optional[List[str]] = Field(default=None, max_length=10)
    location: Optional[str] = Field(default=None, max_length=120)
    min_years: Optional[float] = Field(default=None, ge=0, le=60)
    page: int = Field(default=1, ge=1, le=100)
    page_size: int = Field(default=10, ge=1, le=50)


class CandidateIn(BaseModel):
    person_id: uuid.UUID


class MatchCandidatesIn(BaseModel):
    opportunity_id: uuid.UUID
    page: int = Field(default=1, ge=1, le=100)
    page_size: int = Field(default=10, ge=1, le=50)


class OrgJobsIn(BaseModel):
    status: Optional[str] = Field(default=None, max_length=20)


class OrgApplicationsIn(BaseModel):
    job_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(default=None, max_length=32)


class SendMessageIn(BaseModel):
    conversation_id: uuid.UUID
    body: str = Field(min_length=1, max_length=4000)


class CreateOutreachIn(BaseModel):
    person_id: uuid.UUID
    opportunity_id: Optional[uuid.UUID] = None
    message: str = Field(min_length=1, max_length=2000)
    context: Optional[str] = Field(default=None, max_length=1000)


@dataclass
class AthenaTool:
    name: str
    description: str
    input_model: type[BaseModel]
    modes: Set[str]
    handler: Handler
    permission: Optional[str] = None  # org-scoped permission code
    risk: str = ATHENA_RISK_READ_ONLY
    read_only: bool = True
    data_scope: str = "own"  # own | org | platform
    consent_required: bool = False
    confirmation_required: bool = False
    audit_required: bool = True

    @property
    def schema(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }


# --- Shared helpers ------------------------------------------------------------

def _person_for_user(db: Session, user_id: uuid.UUID) -> PersonProfile:
    person = db.scalars(
        select(PersonProfile).where(PersonProfile.user_id == user_id)
    ).first()
    if person is None:
        raise PermissionDeniedError("No jobseeker profile exists for this account.")
    return person


def _opportunity_summary(db: Session, opp: Opportunity) -> Dict:
    return {
        "id": str(opp.id),
        "title": opp.title,
        "company_name": opp.company_name,
        "location": opp.location,
        "country": opp.country,
        "city": opp.city,
        "work_mode": opp.work_mode,
        "employment_type": opp.employment_type,
        "experience_level": opp.experience_level,
        "industry": opp.industry,
        "skills_required": opp.skills_required or [],
        "min_salary": opp.min_salary,
        "max_salary": opp.max_salary,
        "salary_currency": opp.salary_currency,
        "remote_eligible": opp.remote_eligible,
        "closing_at": opp.closing_at.isoformat() if opp.closing_at else None,
    }


def _match_view(db: Session, person_id: uuid.UUID, opp: Opportunity) -> Dict:
    candidate = matching_service.load_candidate_profile(db, person_id)
    goal = matching_service.load_primary_goal(db, person_id)
    return matching_service.match_opportunity(candidate, opp, goal)


# --- Jobseeker tools (own data / public discovery) -----------------------------

def _get_my_work_id(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    skill_rows = db.execute(
        select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person.id)
    ).all()
    experiences = db.scalars(
        select(WorkExperience)
        .where(WorkExperience.person_id == person.id)
        .order_by(WorkExperience.start_date.desc())
    ).all()
    educations = db.scalars(
        select(Education).where(Education.person_id == person.id)
    ).all()
    credentials = db.scalars(
        select(Credential).where(Credential.person_id == person.id)
    ).all()
    # Data minimization: never include contact/identity-sensitive fields.
    return {
        "person_id": str(person.id),
        "headline": person.headline,
        "summary": (person.summary or "")[:2000],
        "city": person.city,
        "country_code": person.country_code,
        "skills": [
            {"skill": skill.name, "level": us.level, "years_experience": us.years_experience}
            for us, skill in skill_rows
        ],
        "experiences": [
            {
                "role": e.title,
                "company": e.company_name,
                "start_date": e.start_date.isoformat() if e.start_date else None,
                "end_date": e.end_date.isoformat() if e.end_date else None,
                "current": e.is_current,
            }
            for e in experiences
        ],
        "education": [
            {
                "degree": e.degree,
                "institution": e.institution,
                "field": e.field_of_study,
                "level": e.level,
            }
            for e in educations
        ],
        "credentials": [
            {
                "name": c.name,
                "issuer": c.issuer,
                "status": c.status,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None,
            }
            for c in credentials
        ],
    }


def _get_my_skills(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    rows = db.execute(
        select(UserSkill, Skill).join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.person_id == person.id)
    ).all()
    return {
        "skills": [
            {"name": skill.name, "level": us.level, "years_experience": us.years_experience}
            for us, skill in rows
        ]
    }


def _get_my_credentials(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    rows = db.scalars(select(Credential).where(Credential.person_id == person.id)).all()
    return {
        "credentials": [
            {"name": c.name, "issuer": c.issuer, "status": c.status}
            for c in rows
        ]
    }


def _get_my_career_goals(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    rows = db.scalars(
        select(CareerGoal).where(CareerGoal.person_id == person.id)
    ).all()
    return {
        "goals": [
            {
                "title": g.title,
                "target_role": g.target_role,
                "target_industries": g.target_industries or [],
                "target_locations": g.target_locations or [],
                "is_primary": g.is_primary,
            }
            for g in rows
        ]
    }


def _get_my_applications(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    rows = db.scalars(
        select(JobApplication).where(JobApplication.person_id == person.id)
    ).all()
    out = []
    for a in rows:
        opp = db.get(Opportunity, a.opportunity_id)
        out.append(
            {
                "application_id": str(a.id),
                "opportunity_id": str(a.opportunity_id),
                "title": opp.title if opp else None,
                "company_name": opp.company_name if opp else None,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )
    return {"applications": out}


def _get_my_interviews(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    rows = db.scalars(
        select(Interview).where(Interview.person_id == person.id)
    ).all()
    return {
        "interviews": [
            {
                "id": str(i.id),
                "application_id": str(i.application_id),
                "scheduled_at": i.scheduled_at.isoformat() if i.scheduled_at else None,
                "mode": i.mode,
                "status": i.status,
            }
            for i in rows
        ]
    }


def _get_my_offers(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    rows = db.scalars(select(Offer).where(Offer.person_id == person.id)).all()
    return {
        "offers": [
            {
                "id": str(o.id),
                "application_id": str(o.application_id),
                "salary_amount": o.salary_amount,
                "currency": o.currency,
                "status": o.status,
                "expires_at": o.expires_at.isoformat() if o.expires_at else None,
            }
            for o in rows
        ]
    }


def _search_opportunities(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    query = select(Opportunity).where(Opportunity.status == "active")
    if args.get("q"):
        like = f"%{args['q']}%"
        query = query.where(Opportunity.title.ilike(like) | Opportunity.company_name.ilike(like))
    if args.get("skills"):
        query = query.where(Opportunity.skills_required.contains(args["skills"]))
    if args.get("location"):
        query = query.where(Opportunity.city.ilike(f"%{args['location']}%"))
    rows = db.scalars(query.order_by(Opportunity.created_at.desc()).limit(10)).all()
    results = []
    for opp in rows:
        summary = _opportunity_summary(db, opp)
        summary["match"] = _match_view(db, person.id, opp)
        results.append(summary)
    return {"results": results, "count": len(results)}


def _get_opportunity(db: Session, user: User, session, org_id, args) -> Dict:
    opp = db.get(Opportunity, args["opportunity_id"])
    if opp is None:
        from app.core.errors import NotFoundError
        raise NotFoundError("Opportunity not found.")
    person = _person_for_user(db, user.id)
    summary = _opportunity_summary(db, opp)
    summary["match"] = _match_view(db, person.id, opp)
    return summary


def _compare_opportunities(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    out = []
    for opp_id in args["opportunity_ids"]:
        opp = db.get(Opportunity, opp_id)
        if opp is None:
            continue
        summary = _opportunity_summary(db, opp)
        summary["match"] = _match_view(db, person.id, opp)
        out.append(summary)
    return {"opportunities": out}


def _get_application_status(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    app = db.get(JobApplication, args["application_id"])
    if app is None or app.person_id != person.id:
        raise PermissionDeniedError("Application not found or not owned by this account.")
    opp = db.get(Opportunity, app.opportunity_id)
    return {
        "application_id": str(app.id),
        "opportunity_id": str(app.opportunity_id),
        "title": opp.title if opp else None,
        "status": app.status,
        "updated_at": app.updated_at.isoformat() if app.updated_at else None,
    }


def _save_opportunity(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    app = applications_service.save_opportunity(db, person.id, args["opportunity_id"])
    return {"application_id": str(app.id), "status": app.status}


def _apply_to_opportunity(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    app = applications_service.apply(
        db, person.id, args["opportunity_id"], user.id, args.get("cover_note")
    )
    return {"application_id": str(app.id), "status": app.status}


def _list_conversations(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    conversations = communications_service.list_candidate_conversations(db, person.id)
    return {"conversations": conversations}


def _get_conversation(db: Session, user: User, session, org_id, args) -> Dict:
    person = _person_for_user(db, user.id)
    conv = communications_service.get_candidate_conversation(
        db, person.id, args["conversation_id"]
    )
    return communications_service.conversation_out(db, conv)


# --- Employer / recruiter tools (org-scoped, permission-gated) -----------------

def _search_talent(db: Session, user: User, session, org_id, args) -> Dict:
    result = talent_service.search_candidates(
        db,
        org_id,
        user.id,
        q=args.get("q"),
        skills=args.get("skills"),
        location=args.get("location"),
        min_years=args.get("min_years"),
        page=args.get("page", 1),
        page_size=args.get("page_size", 10),
    )
    return result


def _get_candidate(db: Session, user: User, session, org_id, args) -> Dict:
    person_id = args["person_id"]
    if not talent_service.person_visible_to_org(db, person_id, org_id):
        raise PermissionDeniedError("Candidate is not discoverable for this organization.")
    person = talent_service._person(db, person_id)
    return {
        "person_id": str(person.id),
        "display_name": talent_service._display_name(db, person),
        "headline": person.headline,
        "location": talent_service._person_location(person),
        "skills": talent_service._public_skills(db, person_id),
        "experiences": talent_service._public_experiences(db, person_id),
        "education": talent_service._public_educations(db, person_id),
        "years_experience": talent_service._years_experience(db, person_id),
    }


def _match_candidates_for_opportunity(db: Session, user: User, session, org_id, args) -> Dict:
    return talent_service.match_candidates_for_opportunity(
        db,
        org_id,
        args["opportunity_id"],
        user.id,
        page=args.get("page", 1),
        page_size=args.get("page_size", 10),
    )


def _get_org_jobs(db: Session, user: User, session, org_id, args) -> Dict:
    jobs = list_org_jobs(db, org_id, status=args.get("status"))
    return {
        "jobs": [
            {
                "id": str(j.id),
                "title": j.title,
                "status": j.status,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs
        ]
    }


def _get_org_application_status(db: Session, user: User, session, org_id, args) -> Dict:
    app = db.get(JobApplication, args["application_id"])
    if app is None:
        from app.core.errors import NotFoundError
        raise NotFoundError("Application not found.")
    from app.services.company_os import org_opportunity_ids
    if app.opportunity_id not in set(org_opportunity_ids(db, org_id)):
        raise PermissionDeniedError("Application does not belong to this organization.")
    summary = candidate_summary(db, app)
    return {"application_id": str(app.id), "status": app.status, "summary": summary}


def _summarize_org_applications(db: Session, user: User, session, org_id, args) -> Dict:
    apps = list_org_applications(db, org_id, job_id=args.get("job_id"), status=args.get("status"))
    return {
        "count": len(apps),
        "applications": [
            {
                "application_id": str(a.id),
                "opportunity_id": str(a.opportunity_id),
                "status": a.status,
                "person_id": str(a.person_id),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in apps[:50]
        ],
    }


def _list_org_conversations(db: Session, user: User, session, org_id, args) -> Dict:
    conversations = communications_service.list_org_conversations(db, org_id, user.id)
    return {"conversations": conversations}


def _get_org_conversation(db: Session, user: User, session, org_id, args) -> Dict:
    conv = communications_service.get_org_conversation(db, org_id, args["conversation_id"], user.id)
    return communications_service.conversation_out(db, conv)


def _draft_message(db: Session, user: User, session, org_id, args) -> Dict:
    # Drafting is provider-generated TEXT — no database write, no message
    # sent. The provider call happens in the Athena orchestration layer via
    # a dedicated tool; this handler only validates conversation access.
    conv = communications_service.get_org_conversation(
        db, org_id, args["conversation_id"], user.id
    )
    return {"conversation_id": str(conv.id), "draft_ready": True, "hint": (
        "Drafting requires an available AI provider and is completed by the "
        "Athena orchestration layer before any send."
    )}


def _send_message(db: Session, user: User, session, org_id, args) -> Dict:
    conv = communications_service.get_org_conversation(
        db, org_id, args["conversation_id"], user.id
    )
    from app.models.enums import MESSAGE_SIDE_RECRUITER
    message = communications_service.send_message(
        db, conv, user.id, MESSAGE_SIDE_RECRUITER, args["body"]
    )
    return {"message_id": str(message.id), "status": "sent"}


def _create_outreach(db: Session, user: User, session, org_id, args) -> Dict:
    request = outreach_service.create_outreach(
        db,
        org_id,
        user.id,
        person_id=args["person_id"],
        message=args["message"],
        opportunity_id=args.get("opportunity_id"),
        context=args.get("context"),
    )
    return {"outreach_id": str(request.id), "status": request.status}


# --- Registry ------------------------------------------------------------------

TOOLS: Dict[str, AthenaTool] = {}


def _register(tool: AthenaTool) -> None:
    TOOLS[tool.name] = tool


_register(AthenaTool(
    "get_my_work_id", "Returns the caller's own Work ID digest: skills, experience, education, credentials (no contact or identity-sensitive fields).",
    EmptyIn, {ATHENA_MODE_JOBSEEKER}, _get_my_work_id, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "get_my_skills", "Returns the caller's own skills with years and provenance.", EmptyIn,
    {ATHENA_MODE_JOBSEEKER}, _get_my_skills, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "get_my_credentials", "Returns the caller's own credentials (titles, issuers, verification states — never document content).", EmptyIn,
    {ATHENA_MODE_JOBSEEKER}, _get_my_credentials, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "get_my_career_goals", "Returns the caller's own career goals.", EmptyIn,
    {ATHENA_MODE_JOBSEEKER}, _get_my_career_goals, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "get_my_applications", "Lists the caller's own job applications with status.", EmptyIn,
    {ATHENA_MODE_JOBSEEKER}, _get_my_applications, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "get_my_interviews", "Lists the caller's own interviews.", EmptyIn,
    {ATHENA_MODE_JOBSEEKER}, _get_my_interviews, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "get_my_offers", "Lists the caller's own offers.", EmptyIn,
    {ATHENA_MODE_JOBSEEKER}, _get_my_offers, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "search_opportunities", "Searches active opportunities and returns explainable match summaries for the caller.",
    SearchOpportunitiesIn, {ATHENA_MODE_JOBSEEKER}, _search_opportunities, risk=ATHENA_RISK_READ_ONLY, data_scope="public",
))
_register(AthenaTool(
    "get_opportunity", "Returns one opportunity with an explainable match summary.", OpportunityIn,
    {ATHENA_MODE_JOBSEEKER}, _get_opportunity, risk=ATHENA_RISK_READ_ONLY, data_scope="public",
))
_register(AthenaTool(
    "compare_opportunities", "Compares up to 5 opportunities with explainable match summaries.", OpportunityIdsIn,
    {ATHENA_MODE_JOBSEEKER}, _compare_opportunities, risk=ATHENA_RISK_READ_ONLY, data_scope="public",
))
_register(AthenaTool(
    "get_application_status", "Returns the caller's own application status.", ApplicationIn,
    {ATHENA_MODE_JOBSEEKER}, _get_application_status, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "save_opportunity", "Saves an opportunity to the caller's list (low-risk write).", SaveOpportunityIn,
    {ATHENA_MODE_JOBSEEKER}, _save_opportunity, risk=ATHENA_RISK_LOW_RISK_WRITE, read_only=False, data_scope="own",
))
_register(AthenaTool(
    "apply_to_opportunity", "Applies the caller to an opportunity. HIGH-RISK: requires explicit user confirmation.",
    ApplyIn, {ATHENA_MODE_JOBSEEKER}, _apply_to_opportunity, risk=ATHENA_RISK_HIGH_RISK_WRITE,
    read_only=False, confirmation_required=True, data_scope="own",
))
_register(AthenaTool(
    "list_conversations", "Lists the caller's own AskTrabaajo conversations.", EmptyIn,
    {ATHENA_MODE_JOBSEEKER}, _list_conversations, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "get_conversation", "Returns one of the caller's own conversations.", ConversationIn,
    {ATHENA_MODE_JOBSEEKER}, _get_conversation, risk=ATHENA_RISK_READ_ONLY, data_scope="own",
))
_register(AthenaTool(
    "search_talent", "Searches discoverable candidates for the organization (explainable).",
    SearchTalentIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _search_talent,
    permission="candidates.search", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "get_candidate", "Returns a discoverable candidate's public Work ID digest for the organization.",
    CandidateIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _get_candidate,
    permission="candidates.read", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "match_candidates_for_opportunity", "Ranks discoverable candidates for one of the organization's opportunities (explainable).",
    MatchCandidatesIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _match_candidates_for_opportunity,
    permission="candidates.search", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "get_org_jobs", "Lists the organization's own job postings.", OrgJobsIn,
    {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _get_org_jobs,
    permission="jobs.view", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "get_org_application_status", "Returns one of the organization's applications with candidate summary.",
    ApplicationIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _get_org_application_status,
    permission="applications.view", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "summarize_org_applications", "Summarizes the organization's applications, optionally filtered by job/status.",
    OrgApplicationsIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _summarize_org_applications,
    permission="applications.view", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "list_org_conversations", "Lists the organization's AskTrabaajo conversations.", EmptyIn,
    {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _list_org_conversations,
    permission="communications.read", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "get_org_conversation", "Returns one of the organization's conversations.", ConversationIn,
    {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _get_org_conversation,
    permission="communications.read", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "draft_message", "Prepares a message draft for one of the organization's conversations (no message is sent).",
    ConversationIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _draft_message,
    permission="communications.read", risk=ATHENA_RISK_READ_ONLY, data_scope="org",
))
_register(AthenaTool(
    "send_message", "Sends a message in one of the organization's conversations. HIGH-RISK: requires explicit user confirmation.",
    SendMessageIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _send_message,
    permission="communications.send", risk=ATHENA_RISK_HIGH_RISK_WRITE,
    read_only=False, confirmation_required=True, data_scope="org",
))
_register(AthenaTool(
    "create_outreach", "Sends a controlled outreach request to a candidate. HIGH-RISK: requires explicit user confirmation.",
    CreateOutreachIn, {ATHENA_MODE_EMPLOYER, ATHENA_MODE_RECRUITER}, _create_outreach,
    permission="talent.outreach.create", risk=ATHENA_RISK_HIGH_RISK_WRITE,
    read_only=False, confirmation_required=True, data_scope="org",
))


def get_tool(name: str) -> Optional[AthenaTool]:
    return TOOLS.get(name)


def tool_schemas(modes: Set[str]) -> List[Dict]:
    return [t.schema for t in TOOLS.values() if t.modes & modes]


def tools_for_modes(modes: Set[str]) -> List[Dict]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "risk": t.risk,
            "read_only": t.read_only,
            "data_scope": t.data_scope,
            "confirmation_required": t.confirmation_required,
        }
        for t in TOOLS.values()
        if t.modes & modes
    ]