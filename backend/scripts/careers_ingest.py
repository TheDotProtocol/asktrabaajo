#!/usr/bin/env python3
"""Careers-corpus ingestion adapter (Phase 6) — a CONTROLLED import path.

Existing Careers data is a valuable compatibility source; it is NOT deleted
or rewritten. This tool maps portfolio jobs from the careers SQL corpus into
the canonical model:

    EXISTING CAREERS JOB (SQL corpus)
        -> normalize (parse)
        -> validate   (drop records that do not map cleanly, count them)
        -> dedupe     (slug-based, idempotent)
        -> provenance (imported_from='careers_corpus', source + original slug)
        -> canonical JobPosting --published--> canonical Opportunity
        -> jobseeker discovery (the same catalogue Phase 5 built)

Usage (run from backend/, uses the app's env configuration):
    ENVIRONMENT=development DATABASE_URL=postgresql://... \\
        ./.venv/bin/python scripts/careers_ingest.py \\
        --jobs ../scripts/master-portfolio-jobs-part1.sql \\
        --company-name "AR Holdings" --company-slug ar-holdings-group

The demo run can import into an organization: pass
--organization-id <uuid> to attach imported jobs to a real employer tenant.
Without it, jobs land under a deterministic placeholder organization.

PARSER NOTES
------------
The corpus uses INSERT INTO public.jobs (...) SELECT ... with dollar-quoted
($t$...$t$) text, ::uuid/::text[] casts, and boolean/integer/NULL scalars.
The parser is defensive: rows that do not parse cleanly are counted and
skipped (reported at the end) — an import NEVER half-writes a malformed job.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import uuid
from typing import Dict, List, Optional

# Allow running from backend/ without installation.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ENVIRONMENT", "development")

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.career import Opportunity  # noqa: E402
from app.models.company import JobPosting  # noqa: E402
from app.models.tenancy import Organization  # noqa: E402
from app.services.company_os import publish_job, slugify_title  # noqa: E402

# Known AR portfolio company slugs -> display names (provenance mapping).
COMPANY_NAMES = {
    "ar-holdings": "AR Holdings",
    "ar-holdings-group": "AR Holdings",
    "dot-protocol": "Dot Protocol",
    "dot": "Dot Protocol",
    "tau": "Tau",
    "tau-core": "Tau Core",
    "akuma": "Akuma",
    "titan-capital": "Titan Capital",
    "vault": "Vault",
    "aurora": "Aurora Cloud",
    "aurora-cloud": "Aurora Cloud",
    "ar-labs": "AR Labs",
}

_COLUMN_ALIASES = {
    "employment_type": "employment_type",
    "experience_level": "experience_level",
    "salary_min": "salary_min",
    "salary_max": "salary_max",
    "currency": "salary_currency",
    "remote_allowed": "remote_eligible",
    "work_mode": "work_mode",
    "country": "country",
    "city": "city",
    "location": "location",
    "seniority": "seniority",
    "industry": "industry",
}


class CareersJob:
    """A normalized, validated careers job record."""

    def __init__(self, raw: dict) -> None:
        self.raw = raw
        self.slug = raw.get("slug") or ""
        self.title = (raw.get("title") or "").strip()
        self.description = (raw.get("description") or "").strip() or None
        self.summary = (raw.get("role_summary") or "").strip() or None
        self.requirements = raw.get("requirements") or []
        self.skills_required = _extract_skills(self.requirements) or raw.get(
            "skills_required"
        )
        self.location = raw.get("location") or _compose_location(raw)
        self.country = raw.get("country")
        self.city = raw.get("city")
        self.work_mode = _norm_work_mode(raw.get("work_mode"))
        self.employment_type = _norm_employment_type(raw.get("employment_type"))
        self.experience_level = raw.get("experience_level")
        self.seniority = _norm_seniority(raw.get("seniority"))
        self.industry = raw.get("industry")
        self.salary_min = _num(raw.get("salary_min"))
        self.salary_max = _num(raw.get("salary_max"))
        self.currency = raw.get("currency") or raw.get("salary_currency") or "USD"
        self.remote_eligible = _bool(raw.get("remote_allowed")) or self.work_mode == "remote"

    @property
    def company_slug(self) -> Optional[str]:
        if not self.slug:
            return None
        for prefix in sorted(COMPANY_NAMES, key=len, reverse=True):
            if self.slug.startswith(prefix + "-"):
                return prefix
        return None

    @property
    def company_name(self) -> str:
        prefix = self.company_slug
        return COMPANY_NAMES.get(prefix, "AR Holdings Portfolio") if prefix else "AR Holdings Portfolio"

    @property
    def is_valid(self) -> bool:
        return bool(self.title and self.slug)


def _extract_skills(requirements: List[str]) -> Optional[List[str]]:
    """Skills are embedded in requirement lines; extract clean skill tokens."""
    known_skills = [
        "python", "typescript", "javascript", "react", "node", "node.js", "sql",
        "postgresql", "postgres", "aws", "gcp", "kubernetes", "docker", "terraform",
        "solidity", "rust", "go", "java", "c++", "machine learning", "deep learning",
        "nlp", "pytorch", "tensorflow", "blockchain", "distributed systems", "linux",
        "graphql", "figma", "product management", "data analysis", "security",
        "cryptography", "web3", "analytics", "mobile", "ios", "android", "flutter",
        "leadership", "recruiting", "compliance", "excel", "power bi", "cloud",
        "devops", "ci/cd", "observability", "testing", "rest apis",
    ]
    found: List[str] = []
    blob = " ".join(requirements).lower()
    for skill in known_skills:
        if skill in blob:
            found.append(skill)
    return found or None


def _compose_location(raw: dict) -> Optional[str]:
    parts = [p for p in (raw.get("city"), raw.get("country")) if p]
    return ", ".join(parts) if parts else None


def _norm_work_mode(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip().lower()
    if value in {"remote", "hybrid", "onsite", "in-person", "on-site"}:
        return "onsite" if value in {"in-person", "on-site"} else value
    return None


def _norm_employment_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().lower().replace("-", "_")


def _norm_seniority(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = value.strip().lower()
    for level in ("junior", "mid", "senior", "lead", "entry", "executive"):
        if level in value:
            return level
    return None


def _bool(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "t", "1", "yes"}


def _num(value) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# --- corpus parser -------------------------------------------------------------

_INSERT_RE = re.compile(r"INSERT INTO public\.jobs\s*\(", re.IGNORECASE)
_COLUMNS_RE = re.compile(r"^\s*([a-z_]+)\s*,?\s*$", re.MULTILINE)
_SCALAR_DQ = re.compile(r"\$t\$(.*?)\$t\$", re.DOTALL)
_ARRAY_DQ = re.compile(r"ARRAY\s*\[(.*?)\]\s*::text\[\]", re.DOTALL)
_NULL = re.compile(r"^\s*NULL\s*(::[a-z]+)?\s*$", re.IGNORECASE)
_BOOL_RE = re.compile(r"^\s*(true|false)\s*$", re.IGNORECASE)
_NUM_RE = re.compile(r"^\s*(\d+(\.\d+)?)\s*$")

# The corpus SELECT pulls location (and others) from joined company rows,
# so each INSERT ends with a "FROM public.companies ..." tail after the 30
# leading value expressions. Everything from FROM onward is not a value.
_FROM_TAIL = re.compile(r"\bFROM\s+public\.companies\b", re.IGNORECASE | re.DOTALL)


def _split_top_level(text: str, separator: str = ",") -> List[str]:
    """Split on commas that are not inside $t$...$t$ quoting."""
    parts: List[str] = []
    depth = 0
    current: List[str] = []
    i = 0
    while i < len(text):
        if text.startswith("$t$", i):
            end = text.find("$t$", i + 3)
            if end == -1:
                current.append(text[i:])
                break
            current.append(text[i : end + 3])
            i = end + 3
            continue
        ch = text[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth = max(0, depth - 1)
        if ch == separator and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1
    if current:
        parts.append("".join(current).strip())
    return parts


def _parse_array(expr: str) -> List[str]:
    match = _ARRAY_DQ.search(expr)
    if not match:
        return []
    inner = match.group(1)
    return [m.strip() for m in _SCALAR_DQ.findall(inner) if m.strip()]


def _parse_scalar(expr: str):
    expr = expr.strip()
    if _NULL.match(expr):
        return None
    match = _SCALAR_DQ.search(expr)
    if match:
        return match.group(1)
    match = _BOOL_RE.match(expr)
    if match:
        return match.group(1).lower() == "true"
    match = _NUM_RE.match(expr)
    if match:
        return float(match.group(1)) if "." in match.group(1) else int(match.group(1))
    return None


# Column sequence of the corpus INSERT..SELECT after the four subquery
# ids (employer_id, company_id, office_id, department_id). Anchoring on the
# slug token keeps the mapping deterministic even when leading expressions
# wrap values in subqueries/COALESCE.
_VALUE_COLUMNS = [
    "slug", "title", "description", "role_summary", "responsibilities",
    "requirements", "preferred_qualifications", "reporting_manager",
    "work_mode", "hiring_centre", "country", "city", "timezone",
    "visa_sponsorship", "remote_eligibility", "interview_process",
    "equal_opportunity_statement", "job_benefits", "employment_type",
    "experience_level", "salary_min", "salary_max", "currency", "status",
    "remote_allowed", "location",
]

# ARRAY-typed columns in the sequence (value expressed as ARRAY[...]::text[]).
_ARRAY_COLUMNS = {
    "responsibilities", "requirements", "preferred_qualifications",
    "interview_process", "job_benefits",
}


def parse_careers_file(path: str) -> List[CareersJob]:
    """Parse the corpus file into validated CareersJob records."""
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        content = handle.read()

    jobs: List[CareersJob] = []
    positions = [m.start() for m in _INSERT_RE.finditer(content)]
    for index, start in enumerate(positions):
        end = positions[index + 1] if index + 1 < len(positions) else len(content)
        block = content[start:end]
        semi = block.find(";")
        if semi == -1:
            continue
        block = block[: semi + 1]
        columns_start = block.find("(")
        columns_end = block.find(")", columns_start)
        if columns_start == -1 or columns_end == -1:
            continue
        select_pos = block.find("SELECT", columns_end)
        if select_pos == -1:
            continue
        values_src = block[select_pos + len("SELECT"):]
        tail = _FROM_TAIL.search(values_src)
        if tail:
            values_src = values_src[: tail.start()]
        conflict_pos = values_src.find("ON CONFLICT")
        if conflict_pos != -1:
            values_src = values_src[:conflict_pos]
        raw_values = _split_top_level(values_src)

        # Locate the slug token: the first bare $t$..$t$ that is not inside
        # a COALESCE/subquery wrapper is the job slug.
        slug_index = None
        for idx, expr in enumerate(raw_values):
            value = _parse_scalar(expr)
            if value and idx > 0 and not expr.startswith("COALESCE") and "::uuid" not in expr:
                slug_index = idx
                break
        if slug_index is None:
            continue

        raw: Dict[str, object] = {}
        value_exprs = raw_values[slug_index:]
        for name, expr in zip(_VALUE_COLUMNS, value_exprs):
            if name in _ARRAY_COLUMNS:
                raw[name] = _parse_array(expr)
            else:
                raw[name] = _parse_scalar(expr)
        job = CareersJob(raw)
        if job.is_valid:
            jobs.append(job)
    return jobs


# --- import --------------------------------------------------------------------

def import_jobs(
    db: Session,
    jobs: List[CareersJob],
    *,
    organization_id: Optional[uuid.UUID] = None,
) -> Dict:
    """Idempotent import: create JobPostings + published Opportunities."""
    created_jobs, created_opps, skipped, existing = 0, 0, 0, 0

    # Resolve or create the provenance organization.
    org = db.get(Organization, organization_id) if organization_id else None
    if org is None:
        org = db.scalar(
            select(Organization).where(Organization.slug == "careers-corpus-imports")
        )
    if org is None:
        org = Organization(
            name="Careers Corpus (imported)",
            slug="careers-corpus-imports",
            kind="employer",
            status="active",
        )
        db.add(org)
        db.commit()
        db.refresh(org)

    for job in jobs:
        dedupe_key = f"careers:{job.company_slug}:{job.slug}"
        existing_job = db.scalar(
            select(JobPosting).where(JobPosting.imported_from == dedupe_key)
        )
        if existing_job is not None:
            existing += 1
            continue
        posting = JobPosting(
            organization_id=org.id,
            title=job.title,
            slug=f"{job.company_slug or 'careers'}-{job.slug}"[:210],
            summary=job.summary,
            description=job.description,
            requirements=job.requirements,
            skills_required=job.skills_required,
            location=job.location,
            country=job.country,
            city=job.city,
            remote_eligible=job.remote_eligible,
            work_mode=job.work_mode,
            employment_type=job.employment_type,
            experience_level=job.experience_level,
            seniority=job.seniority,
            industry=job.industry or job.company_name,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.currency,
            status="draft",
            imported_from=dedupe_key,
        )
        db.add(posting)
        db.flush()
        # The posting's title slug may differ from dedupe slug; publish now.
        try:
            published = publish_job(db, org.id, posting.id)
            created_jobs += 1
            if published.opportunity_id:
                # publish_job stamps source="platform"; the adapter marks
                # provenance explicitly so imported jobs are never presented
                # as native employer postings.
                opp = db.get(Opportunity, published.opportunity_id)
                if opp is not None:
                    opp.source = "careers_compat"
                    db.commit()
                created_opps += 1
        except Exception:
            skipped += 1
            db.rollback()
    db.commit()
    return {
        "created_jobs": created_jobs,
        "created_opportunities": created_opps,
        "existing": existing,
        "skipped": skipped,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", required=True, help="Path to a careers jobs SQL corpus file")
    parser.add_argument("--organization-id", type=uuid.UUID, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    jobs = parse_careers_file(args.jobs)
    if args.limit:
        jobs = jobs[: args.limit]
    print(f"Parsed {len(jobs)} jobs from {args.jobs}")

    db = SessionLocal()
    try:
        result = import_jobs(db, jobs, organization_id=args.organization_id)
    finally:
        db.close()
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
