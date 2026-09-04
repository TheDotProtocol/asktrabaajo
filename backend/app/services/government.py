"""Government workforce intelligence — privacy-preserving aggregation.

Government APIs never query person rows for display. This service is the
only path from canonical Work ID / opportunity / company tables to a
government response. It returns counts, distributions and suppressed
cells — never person ids, contact fields, documents or messages.

K-threshold policy lives in Settings.government_min_cohort_size.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.company import CompanyProfile, JobPosting
from app.models.enums import JOB_STATUS_PUBLISHED, ORG_KIND_EMPLOYER
from app.models.identity import PersonProfile
from app.models.tenancy import Membership, Organization
from app.models.work import Education, Skill, UserSkill, WorkExperience
from app.services import authz

STATUS_OK = "ok"
STATUS_SUPPRESSED = "suppressed"
STATUS_INSUFFICIENT = "insufficient_cohort"
PRIVACY_NOTE = (
    "Privacy-protected aggregate data. Individual records are not exposed."
)


@dataclass(frozen=True)
class IntelligenceFilters:
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    skill: Optional[str] = None

    def active_person_dimensions(self) -> int:
        return sum(
            1
            for value in (self.country, self.state_province, self.city, self.skill)
            if value
        )

    def as_scope(self) -> Dict[str, str]:
        return {
            key: value
            for key, value in {
                "country": self.country,
                "state_province": self.state_province,
                "city": self.city,
                "industry": self.industry,
                "skill": self.skill,
            }.items()
            if value
        }


def min_cohort_size() -> int:
    return max(1, int(get_settings().government_min_cohort_size))


def parse_filters(
    *,
    country: Optional[str] = None,
    state_province: Optional[str] = None,
    city: Optional[str] = None,
    industry: Optional[str] = None,
    skill: Optional[str] = None,
) -> IntelligenceFilters:
    def _clean(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        if not text or text.lower() in {"all", "*"}:
            return None
        if len(text) > 80:
            from app.core.errors import InvalidInputError

            raise InvalidInputError("Filter value is too long.")
        return text

    return IntelligenceFilters(
        country=_clean(country),
        state_province=_clean(state_province),
        city=_clean(city),
        industry=_clean(industry),
        skill=_clean(skill),
    )


def require_government_reader(
    db: Session, user_id, organization_id=None
) -> Optional[Membership]:
    """Authorize aggregate reads. Backend is authoritative.

    A government-kind membership with workforce.aggregates.read, or a
    platform super admin, may proceed. Employer/candidate memberships never
    satisfy this on their own.
    """
    authz.require_permission(
        db, user_id, "workforce.aggregates.read", organization_id
    )
    if organization_id is not None:
        membership = authz.require_membership(db, user_id, organization_id)
        org = db.get(Organization, organization_id)
        if org is None or org.kind != "government":
            from app.core.errors import PermissionDeniedError

            raise PermissionDeniedError(
                "Government intelligence requires a government organization."
            )
        return membership
    if authz.is_platform_super_admin(db, user_id):
        return None
    rows = db.execute(
        select(Membership)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(
            Membership.user_id == user_id,
            Organization.kind == "government",
        )
    ).scalars().all()
    if not rows:
        from app.core.errors import PermissionDeniedError

        raise PermissionDeniedError(
            "Government intelligence requires a government organization membership."
        )
    return rows[0]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _envelope(payload: Dict[str, Any], filters: IntelligenceFilters) -> Dict[str, Any]:
    return {
        "privacy": PRIVACY_NOTE,
        "privacy_threshold": min_cohort_size(),
        "freshness": "live_aggregate",
        "generated_at": _now().isoformat(),
        "period": "current_snapshot",
        "filters": filters.as_scope(),
        **payload,
    }


def _count_or_suppress(n: int) -> Dict[str, Any]:
    k = min_cohort_size()
    if n < k:
        return {
            "value": None,
            "status": STATUS_SUPPRESSED if n > 0 else STATUS_INSUFFICIENT,
            "label": "SUPPRESSED" if n > 0 else "INSUFFICIENT_COHORT",
        }
    return {"value": n, "status": STATUS_OK, "label": "ok"}


def _buckets_from_rows(
    rows: Sequence[Tuple[Optional[str], int]],
    *,
    unknown_label: str = "Unknown",
) -> Dict[str, Any]:
    """Convert person-cohort (key, count) rows.

    Suppressed cells never include the count. When any cell is suppressed,
    totals are omitted so complementary subtraction cannot reconstruct the
    hidden cohort.
    """
    k = min_cohort_size()
    buckets: List[Dict[str, Any]] = []
    any_suppressed = False
    visible_sum = 0
    for raw_key, count in rows:
        key = (raw_key or "").strip() or unknown_label
        if count < k:
            any_suppressed = True
            buckets.append(
                {
                    "key": key,
                    "value": None,
                    "status": STATUS_SUPPRESSED if count > 0 else STATUS_INSUFFICIENT,
                }
            )
        else:
            visible_sum += count
            buckets.append({"key": key, "value": int(count), "status": STATUS_OK})
    return {
        "buckets": buckets,
        "any_suppressed": any_suppressed,
        "visible_sum": None if any_suppressed else visible_sum,
    }


def _volume_buckets(
    rows: Sequence[Tuple[Optional[str], int]],
    *,
    unknown_label: str = "Unspecified",
) -> Dict[str, Any]:
    """Opportunity / employer volume — not a person cohort.

    Small job or company counts are shown. Names, contacts and private
    fields are never included.
    """
    buckets: List[Dict[str, Any]] = []
    total = 0
    for raw_key, count in rows:
        key = (raw_key or "").strip() or unknown_label
        n = int(count)
        total += n
        buckets.append({"key": key, "value": n, "status": STATUS_OK})
    return {
        "buckets": buckets,
        "any_suppressed": False,
        "visible_sum": total,
    }


def _person_base(filters: IntelligenceFilters):
    stmt = select(PersonProfile.id)
    if filters.country:
        stmt = stmt.where(func.lower(PersonProfile.country_code) == filters.country.lower())
    if filters.state_province:
        stmt = stmt.where(
            func.lower(PersonProfile.state_province) == filters.state_province.lower()
        )
    if filters.city:
        stmt = stmt.where(func.lower(PersonProfile.city) == filters.city.lower())
    if filters.skill:
        stmt = (
            stmt.join(UserSkill, UserSkill.person_id == PersonProfile.id)
            .join(Skill, Skill.id == UserSkill.skill_id)
            .where(func.lower(Skill.name) == filters.skill.lower())
            .distinct()
        )
    return stmt


def _filtered_person_count(db: Session, filters: IntelligenceFilters) -> int:
    return int(db.scalar(select(func.count()).select_from(_person_base(filters).subquery())) or 0)


def _population_gate(db: Session, filters: IntelligenceFilters) -> Optional[Dict[str, Any]]:
    """If the filtered person population is below K, refuse breakdowns."""
    n = _filtered_person_count(db, filters)
    if filters.active_person_dimensions() == 0:
        return None
    if n < min_cohort_size():
        return _envelope(
            {
                "status": STATUS_INSUFFICIENT,
                "message": "INSUFFICIENT_COHORT — the filtered population is below the privacy threshold.",
                "workforce": _count_or_suppress(n),
            },
            filters,
        )
    return None


def overview(db: Session, filters: IntelligenceFilters) -> Dict[str, Any]:
    gated = _population_gate(db, filters)
    if gated:
        return gated

    workforce = _filtered_person_count(db, filters)
    current_employed = int(
        db.scalar(
            select(func.count(func.distinct(WorkExperience.person_id))).where(
                WorkExperience.is_current.is_(True),
                WorkExperience.person_id.in_(_person_base(filters)),
            )
        )
        or 0
    )
    employers = int(
        db.scalar(
            select(func.count()).select_from(Organization).where(
                Organization.kind == ORG_KIND_EMPLOYER
            )
        )
        or 0
    )
    if filters.industry:
        employers = int(
            db.scalar(
                select(func.count())
                .select_from(CompanyProfile)
                .where(func.lower(CompanyProfile.industry) == filters.industry.lower())
            )
            or 0
        )
    open_jobs = _open_job_stmt(filters)
    opportunities = int(db.scalar(select(func.count()).select_from(open_jobs.subquery())) or 0)

    skill_rows = db.execute(
        select(Skill.name, func.count(func.distinct(UserSkill.person_id)))
        .join(UserSkill, UserSkill.skill_id == Skill.id)
        .where(UserSkill.person_id.in_(_person_base(filters)))
        .group_by(Skill.name)
        .order_by(func.count(func.distinct(UserSkill.person_id)).desc())
        .limit(12)
    ).all()

    return _envelope(
        {
            "status": STATUS_OK,
            "cards": {
                "registered_workforce": _count_or_suppress(workforce),
                "current_employment_records": _count_or_suppress(current_employed),
                "active_employers": {"value": employers, "status": STATUS_OK, "label": "organization_count"},
                "open_opportunities": {
                    "value": opportunities,
                    "status": STATUS_OK,
                    "label": "opportunity_count",
                },
            },
            "top_skills": _buckets_from_rows(skill_rows),
            "emerging_skills": {
                "status": STATUS_INSUFFICIENT,
                "message": "INSUFFICIENT DATA — no historical skill snapshots exist yet.",
            },
        },
        filters,
    )


def workforce_distribution(
    db: Session, filters: IntelligenceFilters, group_by: str
) -> Dict[str, Any]:
    allowed = {
        "country": PersonProfile.country_code,
        "state": PersonProfile.state_province,
        "city": PersonProfile.city,
        "education": Education.level,
        "employment": WorkExperience.is_current,
    }
    if group_by not in allowed:
        from app.core.errors import InvalidInputError

        raise InvalidInputError("Unsupported workforce grouping.")
    gated = _population_gate(db, filters)
    if gated:
        return gated

    base = _person_base(filters)
    if group_by == "education":
        rows = db.execute(
            select(Education.level, func.count(func.distinct(Education.person_id)))
            .where(Education.person_id.in_(base))
            .group_by(Education.level)
        ).all()
    elif group_by == "employment":
        current_ids = select(WorkExperience.person_id).where(
            WorkExperience.is_current.is_(True)
        )
        rows = db.execute(
            select(
                case((PersonProfile.id.in_(current_ids), "current_employment_record"), else_="no_current_employment_record"),
                func.count(),
            )
            .where(PersonProfile.id.in_(base))
            .group_by(
                case((PersonProfile.id.in_(current_ids), "current_employment_record"), else_="no_current_employment_record")
            )
        ).all()
    else:
        col = allowed[group_by]
        rows = db.execute(
            select(col, func.count()).where(PersonProfile.id.in_(base)).group_by(col)
        ).all()

    return _envelope(
        {"status": STATUS_OK, "group_by": group_by, **_buckets_from_rows(rows)},
        filters,
    )


def _open_job_stmt(filters: IntelligenceFilters):
    stmt = select(JobPosting.id).where(JobPosting.status == JOB_STATUS_PUBLISHED)
    if filters.country:
        stmt = stmt.where(func.lower(JobPosting.country) == filters.country.lower())
    if filters.city:
        stmt = stmt.where(func.lower(JobPosting.city) == filters.city.lower())
    if filters.industry:
        stmt = stmt.where(func.lower(JobPosting.industry) == filters.industry.lower())
    return stmt


def skills_intelligence(db: Session, filters: IntelligenceFilters) -> Dict[str, Any]:
    gated = _population_gate(db, filters)
    if gated:
        return gated

    supply_rows = db.execute(
        select(Skill.name, func.count(func.distinct(UserSkill.person_id)))
        .join(UserSkill, UserSkill.skill_id == Skill.id)
        .where(UserSkill.person_id.in_(_person_base(filters)))
        .group_by(Skill.name)
        .order_by(func.count(func.distinct(UserSkill.person_id)).desc())
        .limit(40)
    ).all()
    supply = _buckets_from_rows(supply_rows)

    demand_map: Dict[str, int] = {}
    jobs = db.execute(
        select(JobPosting.skills_required).where(
            JobPosting.id.in_(_open_job_stmt(filters))
        )
    ).all()
    for (skills,) in jobs:
        for raw in skills or []:
            name = str(raw).strip()
            if not name:
                continue
            if filters.skill and name.lower() != filters.skill.lower():
                continue
            demand_map[name] = demand_map.get(name, 0) + 1
    demand_rows = sorted(demand_map.items(), key=lambda item: item[1], reverse=True)[:40]
    demand = {
        "buckets": [
            {"key": name, "value": count, "status": STATUS_OK} for name, count in demand_rows
        ],
        "any_suppressed": False,
        "visible_sum": sum(count for _, count in demand_rows),
        "unit": "open_opportunities",
    }

    supply_lookup = {
        row["key"].lower(): row for row in supply["buckets"] if row["status"] == STATUS_OK
    }
    gaps: List[Dict[str, Any]] = []
    for name, demand_n in demand_rows:
        supply_row = supply_lookup.get(name.lower())
        if supply_row is None:
            gaps.append(
                {
                    "key": name,
                    "demand": demand_n,
                    "supply": None,
                    "gap": None,
                    "status": STATUS_INSUFFICIENT,
                    "message": "INSUFFICIENT DATA — supply is suppressed or unobserved.",
                }
            )
            continue
        supply_n = int(supply_row["value"])
        gaps.append(
            {
                "key": name,
                "demand": demand_n,
                "supply": supply_n,
                "gap": demand_n - supply_n,
                "status": STATUS_OK,
            }
        )

    return _envelope(
        {"status": STATUS_OK, "supply": supply, "demand": demand, "gaps": gaps},
        filters,
    )


def geography(db: Session, filters: IntelligenceFilters) -> Dict[str, Any]:
    return workforce_distribution(db, filters, "city")


def industries(db: Session, filters: IntelligenceFilters) -> Dict[str, Any]:
    stmt = (
        select(JobPosting.industry, func.count())
        .where(JobPosting.status == JOB_STATUS_PUBLISHED)
        .group_by(JobPosting.industry)
    )
    if filters.country:
        stmt = stmt.where(func.lower(JobPosting.country) == filters.country.lower())
    if filters.city:
        stmt = stmt.where(func.lower(JobPosting.city) == filters.city.lower())
    rows = db.execute(stmt).all()
    return _envelope(
        {
            "status": STATUS_OK,
            "unit": "open_opportunities",
            "note": "Industry distribution of published opportunities. Not labelled as economic growth.",
            **_volume_buckets(rows, unknown_label="Unspecified"),
        },
        filters,
    )


def opportunities(db: Session, filters: IntelligenceFilters, group_by: str) -> Dict[str, Any]:
    columns = {
        "industry": JobPosting.industry,
        "country": JobPosting.country,
        "city": JobPosting.city,
        "work_mode": JobPosting.work_mode,
        "employment_type": JobPosting.employment_type,
        "experience_level": JobPosting.experience_level,
    }
    if group_by not in columns:
        from app.core.errors import InvalidInputError

        raise InvalidInputError("Unsupported opportunity grouping.")
    col = columns[group_by]
    stmt = (
        select(col, func.count())
        .where(JobPosting.status == JOB_STATUS_PUBLISHED)
        .group_by(col)
    )
    if filters.country:
        stmt = stmt.where(func.lower(JobPosting.country) == filters.country.lower())
    if filters.city:
        stmt = stmt.where(func.lower(JobPosting.city) == filters.city.lower())
    if filters.industry:
        stmt = stmt.where(func.lower(JobPosting.industry) == filters.industry.lower())
    rows = db.execute(stmt).all()
    return _envelope(
        {
            "status": STATUS_OK,
            "group_by": group_by,
            "unit": "open_opportunities",
            "metric": "hiring_demand",
            **_volume_buckets(rows, unknown_label="Unspecified"),
        },
        filters,
    )


def companies(db: Session, filters: IntelligenceFilters) -> Dict[str, Any]:
    stmt = select(CompanyProfile.industry, func.count()).group_by(CompanyProfile.industry)
    filtered = select(func.count()).select_from(CompanyProfile)
    if filters.industry:
        stmt = stmt.where(func.lower(CompanyProfile.industry) == filters.industry.lower())
        filtered = filtered.where(func.lower(CompanyProfile.industry) == filters.industry.lower())
    if filters.country:
        stmt = stmt.where(func.lower(CompanyProfile.country) == filters.country.lower())
        filtered = filtered.where(func.lower(CompanyProfile.country) == filters.country.lower())
    if filters.city:
        stmt = stmt.where(func.lower(CompanyProfile.city) == filters.city.lower())
        filtered = filtered.where(func.lower(CompanyProfile.city) == filters.city.lower())
    rows = db.execute(stmt).all()
    total = int(db.scalar(filtered) or 0)
    return _envelope(
        {
            "status": STATUS_OK,
            "unit": "employer_organizations",
            "active_employers": {"value": total, "status": STATUS_OK},
            "note": "Organization counts only. Company names, contacts and private profiles are not included.",
            **_volume_buckets(rows, unknown_label="Unspecified"),
        },
        filters,
    )


def report(db: Session, kind: str, filters: IntelligenceFilters) -> Dict[str, Any]:
    builders = {
        "workforce": lambda: overview(db, filters),
        "skills": lambda: skills_intelligence(db, filters),
        "regional": lambda: geography(db, filters),
        "industry": lambda: industries(db, filters),
        "hiring_demand": lambda: opportunities(db, filters, "industry"),
        "skill_gap": lambda: skills_intelligence(db, filters),
    }
    if kind not in builders:
        from app.core.errors import InvalidInputError

        raise InvalidInputError("Unknown report kind.")
    body = builders[kind]()
    return {
        "kind": kind,
        "title": {
            "workforce": "Workforce Report",
            "skills": "Skills Report",
            "regional": "Regional Workforce Report",
            "industry": "Industry Report",
            "hiring_demand": "Hiring Demand Report",
            "skill_gap": "Skill Gap Report",
        }[kind],
        "reproducible": True,
        "contains_person_records": False,
        **body,
    }


def export_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten aggregate buckets for CSV/JSON. Never includes person fields."""
    rows: List[Dict[str, Any]] = []
    for section, value in payload.items():
        if isinstance(value, dict) and "buckets" in value:
            for bucket in value["buckets"]:
                rows.append(
                    {
                        "section": section,
                        "key": bucket.get("key"),
                        "value": bucket.get("value"),
                        "status": bucket.get("status"),
                    }
                )
        if section == "gaps" and isinstance(value, list):
            for gap in value:
                rows.append(
                    {
                        "section": "gaps",
                        "key": gap.get("key"),
                        "value": gap.get("gap"),
                        "status": gap.get("status"),
                    }
                )
    return rows


def settings_view(db: Session, user_id) -> Dict[str, Any]:
    memberships = db.execute(
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user_id, Organization.kind == "government")
    ).all()
    return {
        "privacy": PRIVACY_NOTE,
        "privacy_threshold": min_cohort_size(),
        "freshness": "live_aggregate",
        "dataset_scope": "platform_wide_aggregates",
        "individual_lookup": False,
        "consent_disclosure": "FUTURE / NOT IMPLEMENTED",
        "investment_workflows": "FUTURE CAPABILITY",
        "government_industry_outreach": "FUTURE / NOT IMPLEMENTED",
        "memberships": [
            {
                "organization_id": str(org.id),
                "organization_name": org.name,
                "role": membership.role_code,
            }
            for membership, org in memberships
        ],
    }
