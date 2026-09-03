"""Skill taxonomy registry — normalization, resolution, evidence, requirements.

Single-authority rules for Phase 7 skill intelligence:
- ``Skill`` (``app.models.work``) is the canonical taxonomy row; free-text
  input NEVER silently becomes a new canonical skill when it resolves to an
  existing one.
- ``normalize()`` produces a deterministic token (lowercase, dots removed,
  whitespace collapsed) used for alias lookups. ``skill_aliases.alias``
  stores these tokens and is globally unique, so one alias can never point
  at two skills.
- ``canonical_name_map`` resolves a batch of raw names to canonical skill
  names in constant-ish DB work (two indexed queries), preserving the raw
  value whenever nothing resolves — matching keeps working on free text.
- ``refresh_person_evidence`` derives SkillEvidence rows from the person's
  OWN Work ID records (self-declared skills, experiences, employments,
  credentials). Verification mirrors the source record: a skill is NEVER
  shown as verified unless an authoritative record says so.
- ``normalize_opportunity_requirements`` turns an opportunity's required
  skills into structured rows that preserve the employer's raw wording.
"""
from __future__ import annotations

import re
import uuid
from typing import Dict, Iterable, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import (
    CREDENTIAL_STATUS_VERIFIED,
    SKILL_EVIDENCE_CERTIFICATION,
    SKILL_EVIDENCE_EMPLOYMENT,
    SKILL_EVIDENCE_EXPERIENCE,
    SKILL_EVIDENCE_SELF,
    SKILL_STATUS_ACTIVE,
    VERIFICATION_UNVERIFIED,
    VERIFICATION_VERIFIED,
)
from app.models.talent import (
    OpportunityRequirement,
    SkillAlias,
    SkillEvidence,
    SkillRelationship,
)
from app.models.work import (
    Credential,
    Education,
    Employment,
    Skill,
    UserSkill,
    WorkExperience,
)

_MIN_YEARS_RE = re.compile(r"(\d{1,2})(?:\+)?\s*(?:years?|yrs?|year)", re.IGNORECASE)


def normalize(text: str) -> str:
    """Deterministic normalization for alias lookup.

    ``React.js``/``ReactJS`` -> ``reactjs``; ``Node.js`` -> ``nodejs``;
    whitespace collapses. Symbols such as ``#`` and ``+`` are preserved so
    ``C#`` and ``C++`` do not collapse into unrelated tokens.
    """
    token = text.lower().strip().replace(".", "")
    return " ".join(token.split())


def _display_name(raw: str) -> str:
    """Trimmed original (title-cased for brand-new free-text skills)."""
    cleaned = " ".join(raw.strip().split())
    return cleaned


def find_by_name(db: Session, name: str) -> Optional[Skill]:
    return db.scalar(
        select(Skill)
        .where(func.lower(Skill.name) == name.strip().lower())
        .order_by(Skill.id.asc())
        .limit(1)
    )


def find_by_alias(db: Session, token: str) -> Optional[Skill]:
    alias_row = db.scalar(
        select(SkillAlias).where(SkillAlias.alias == token).limit(1)
    )
    if alias_row is None:
        return None
    return db.get(Skill, alias_row.skill_id)


def resolve_skill(db: Session, raw: str) -> Optional[Skill]:
    """Resolve raw text to a canonical Skill, or None."""
    text = raw.strip()
    if not text:
        return None
    by_name = find_by_name(db, text)
    if by_name is not None:
        return by_name
    return find_by_alias(db, normalize(text))


def canonical_name_map(db: Session, names: Iterable[str]) -> Dict[str, str]:
    """Map a batch of raw names to canonical skill names.

    Resolution order per name: exact case-insensitive skill name, then
    normalized alias. Names that resolve nowhere map to themselves so the
    matching engine keeps behaving on free text.
    """
    unique = sorted({n.strip() for n in names if n and str(n).strip()})
    if not unique:
        return {}
    lower_to_raw = {n.lower(): n for n in unique}

    # 1) Exact skill-name matches (case-insensitive).
    rows = db.execute(
        select(Skill.name).where(func.lower(Skill.name).in_(list(lower_to_raw)))
    ).all()
    result: Dict[str, str] = {}
    for (canonical,) in rows:
        raw = lower_to_raw.get(canonical.lower())
        if raw is not None:
            result[raw] = canonical

    # 2) Normalized alias matches for the remaining names.
    remaining = [n for n in unique if n not in result]
    if remaining:
        tokens = {normalize(n) for n in remaining}
        alias_rows = db.execute(
            select(SkillAlias.alias, Skill.name)
            .join(Skill, Skill.id == SkillAlias.skill_id)
            .where(SkillAlias.alias.in_(tokens))
        ).all()
        alias_to_canonical = {alias: canonical for alias, canonical in alias_rows}
        for n in remaining:
            canonical = alias_to_canonical.get(normalize(n))
            if canonical is not None:
                result[n] = canonical

    # 3) Fallback: unchanged raw value.
    for n in unique:
        result.setdefault(n, n)
    return result


def ensure_skill(
    db: Session,
    raw: str,
    category: str = "general",
    source: str = "manual",
) -> Skill:
    """Return the canonical skill for ``raw``, creating one when no alias or
    skill resolves (new free-text skill + its canonical alias)."""
    existing = resolve_skill(db, raw)
    if existing is not None:
        return existing
    display = _display_name(raw)
    token = normalize(display)
    skill = db.scalar(
        select(Skill)
        .where(func.lower(Skill.name) == display.lower())
        .limit(1)
    )
    if skill is None:
        skill = Skill(name=display, category=category, status=SKILL_STATUS_ACTIVE)
        db.add(skill)
        db.flush()
    if token and not db.scalar(
        select(SkillAlias.id).where(SkillAlias.alias == token).limit(1)
    ):
        db.add(
            SkillAlias(
                skill_id=skill.id, alias=token, original=display, source=source
            )
        )
        db.flush()
    return skill


# --- taxonomy browsing -------------------------------------------------------


def list_taxonomy(
    db: Session,
    q: Optional[str] = None,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    query = select(Skill).where(Skill.status == SKILL_STATUS_ACTIVE)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            func.lower(Skill.name).ilike(like)
            | func.lower(Skill.category).ilike(like)
        )
    if category:
        query = query.where(Skill.category == category)
    total = len(db.scalars(select(func.count()).select_from(query.subquery())).all())
    skills = db.scalars(
        query.order_by(Skill.category, Skill.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"total": total, "page": page, "page_size": page_size, "items": skills}


def taxonomy_categories(db: Session) -> List[str]:
    rows = db.execute(
        select(Skill.category)
        .where(Skill.status == SKILL_STATUS_ACTIVE)
        .distinct()
        .order_by(Skill.category)
    ).all()
    return [r[0] for r in rows]


def skill_detail(db: Session, skill_id: uuid.UUID) -> Optional[dict]:
    skill = db.get(Skill, skill_id)
    if skill is None:
        return None
    aliases = db.scalars(
        select(SkillAlias.original).where(SkillAlias.skill_id == skill.id)
    ).all()
    parents = db.execute(
        select(SkillRelationship.kind, Skill.name)
        .join(Skill, Skill.id == SkillRelationship.related_skill_id)
        .where(
            SkillRelationship.skill_id == skill.id,
            SkillRelationship.kind == "parent",
        )
    ).all()
    related = db.execute(
        select(SkillRelationship.kind, Skill.name)
        .join(Skill, Skill.id == SkillRelationship.related_skill_id)
        .where(
            SkillRelationship.skill_id == skill.id,
            SkillRelationship.kind.in_(["related", "complementary", "similar"]),
        )
    ).all()
    return {
        "id": str(skill.id),
        "name": skill.name,
        "category": skill.category,
        "subcategory": skill.subcategory,
        "description": skill.description,
        "status": skill.status,
        "aliases": [a for a in aliases if a],
        "parents": [{"kind": k, "name": n} for k, n in parents],
        "related": [{"kind": k, "name": n} for k, n in related],
    }


# --- evidence ----------------------------------------------------------------


def _record_verification_status(value: Optional[str]) -> str:
    if value in {VERIFICATION_VERIFIED, CREDENTIAL_STATUS_VERIFIED}:
        return VERIFICATION_VERIFIED
    return VERIFICATION_UNVERIFIED


def refresh_person_evidence(db: Session, person_id: uuid.UUID) -> Dict[str, int]:
    """Derive and persist SkillEvidence rows from the person's Work ID.

    Evidence is fully derived (delete + rebuild), so it always mirrors the
    current records. Verification state comes from the source record.
    """
    db.execute(
        SkillEvidence.__table__.delete().where(
            SkillEvidence.person_id == person_id
        )
    )

    def _add(skill: Optional[Skill], evidence_type: str, reference_type: str,
             reference_id: uuid.UUID, verification: str) -> None:
        if skill is None:
            return
        exists = db.scalar(
            select(SkillEvidence.id).where(
                SkillEvidence.person_id == person_id,
                SkillEvidence.skill_id == skill.id,
                SkillEvidence.reference_type == reference_type,
                SkillEvidence.reference_id == reference_id,
            ).limit(1)
        )
        if exists is None:
            db.add(
                SkillEvidence(
                    person_id=person_id,
                    skill_id=skill.id,
                    evidence_type=evidence_type,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    source="work_id",
                    verification_status=verification,
                )
            )

    counts = {"self": 0, "experience": 0, "employment": 0, "certification": 0}

    self_skills = db.scalars(
        select(UserSkill).where(UserSkill.person_id == person_id)
    ).all()
    for us in self_skills:
        skill = db.get(Skill, us.skill_id)
        _add(skill, SKILL_EVIDENCE_SELF, "user_skill", us.id, VERIFICATION_UNVERIFIED)
        counts["self"] += 1

    experiences = db.scalars(
        select(WorkExperience).where(WorkExperience.person_id == person_id)
    ).all()
    for exp in experiences:
        for raw in exp.skills_used or []:
            skill = resolve_skill(db, str(raw))
            _add(skill, SKILL_EVIDENCE_EXPERIENCE, "work_experience", exp.id,
                 _record_verification_status(exp.verification_status))
            if skill is not None:
                counts["experience"] += 1

    employments = db.scalars(
        select(Employment).where(Employment.person_id == person_id)
    ).all()
    for emp in employments:
        for raw in emp.skills_used or []:
            skill = resolve_skill(db, str(raw))
            _add(skill, SKILL_EVIDENCE_EMPLOYMENT, "employment", emp.id,
                 _record_verification_status(emp.verification_status))
            if skill is not None:
                counts["employment"] += 1

    credentials = db.scalars(
        select(Credential).where(Credential.person_id == person_id)
    ).all()
    for cred in credentials:
        if cred.name:
            skill = resolve_skill(db, cred.name)
            _add(skill, SKILL_EVIDENCE_CERTIFICATION, "credential", cred.id,
                 _record_verification_status(cred.status))
            if skill is not None:
                counts["certification"] += 1

    db.flush()
    return counts


def evidence_for_skills(
    db: Session, person_id: uuid.UUID
) -> Dict[str, List[dict]]:
    """Skill -> evidence rows (live, current Work ID state)."""
    rows = db.execute(
        select(SkillEvidence, Skill.name)
        .join(Skill, Skill.id == SkillEvidence.skill_id)
        .where(SkillEvidence.person_id == person_id)
        .order_by(Skill.name)
    ).all()
    result: Dict[str, List[dict]] = {}
    for ev, name in rows:
        result.setdefault(name, []).append(
            {
                "evidence_type": ev.evidence_type,
                "reference_type": ev.reference_type,
                "verification_status": ev.verification_status,
                "source": ev.source,
            }
        )
    return result


# --- opportunity requirements --------------------------------------------------


def normalize_opportunity_requirements(
    db: Session, opportunity
) -> List[OpportunityRequirement]:
    """Persist structured requirements for one opportunity.

    Preserves the raw employer wording and links each to a canonical skill
    when one resolves. Idempotent per (opportunity_id, raw_text).
    """
    raw_items = [str(s).strip() for s in (opportunity.skills_required or []) if str(s).strip()]
    if not raw_items:
        return []
    existing = {
        r.raw_text: r
        for r in db.scalars(
            select(OpportunityRequirement).where(
                OpportunityRequirement.opportunity_id == opportunity.id
            )
        ).all()
    }
    name_map = canonical_name_map(db, raw_items)
    created: List[OpportunityRequirement] = []
    for raw in raw_items:
        canonical = name_map.get(raw, raw)
        skill = None
        if canonical != raw:
            skill = resolve_skill(db, canonical) or resolve_skill(db, raw)
        if skill is None:
            skill = resolve_skill(db, raw)
        if skill is None:
            # Prose requirement: link a skill only when EXACTLY ONE word
            # resolves, so we never invent requirements the employer did not
            # give. Ambiguous sentences stay unlinked (raw text preserved).
            resolved = {
                resolved.id: resolved
                for token in _words(raw)
                if (resolved := resolve_skill(db, token)) is not None
            }
            if len(resolved) == 1:
                skill = next(iter(resolved.values()))
        row = existing.get(raw)
        if row is None:
            row = OpportunityRequirement(
                opportunity_id=opportunity.id,
                raw_text=raw[:400],
                skill_id=skill.id if skill else None,
                requirement_kind="required",
                min_years=_min_years(raw),
            )
            db.add(row)
            created.append(row)
        else:
            # keep existing rows; refresh link if taxonomy grew meanwhile
            if row.skill_id is None and skill is not None:
                row.skill_id = skill.id
            if row.min_years is None:
                row.min_years = _min_years(raw)
    db.flush()
    return created


def _min_years(raw: str) -> Optional[float]:
    m = _MIN_YEARS_RE.search(raw)
    return float(m.group(1)) if m else None


def _words(raw: str) -> List[str]:
    """Word-ish tokens for prose requirements (keeps # and + intact)."""
    return [
        t for t in re.split(r"[^\w+#]+", raw)
        if t and not t.isdigit()
    ]
