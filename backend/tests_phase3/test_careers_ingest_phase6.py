"""Careers-ingestion adapter tests (Phase 6).

The existing Careers corpus is a valuable compatibility source and is never
deleted or rewritten. These tests prove the CONTROLLED adapter path:

    careers SQL corpus -> normalize -> validate -> dedupe -> provenance
    -> canonical JobPosting (published) -> canonical Opportunity (careers_compat)

The parser is exercised against the REAL corpus file so a future corpus-format
change fails loudly instead of silently importing zero rows.
"""
import os
from pathlib import Path

import pytest

from app.models.career import Opportunity
from app.models.company import JobPosting
from app.models.tenancy import Organization
from scripts.careers_ingest import import_jobs, parse_careers_file

# pytest runs from backend/; corpus lives in the repo scripts/ directory.
CORPUS_CANDIDATES = [
    Path(__file__).resolve().parents[2] / "scripts" / "master-portfolio-jobs-part1.sql",
    Path.cwd().parent / "scripts" / "master-portfolio-jobs-part1.sql",
]

CORPUS = next((p for p in CORPUS_CANDIDATES if p.exists()), None)


def _skip_if_no_corpus():
    if CORPUS is None:
        pytest.skip("careers corpus file not found")


def test_parser_reads_real_corpus_format():
    _skip_if_no_corpus()
    jobs = parse_careers_file(str(CORPUS))
    assert len(jobs) >= 20, f"expected >=20 parsed jobs, got {len(jobs)}"
    for job in jobs:
        assert job.is_valid
        assert job.slug and job.title
        assert job.work_mode in {"remote", "hybrid", "onsite"}
        assert job.employment_type == "full_time"
    # Dedupe safety: corpus slugs are globally unique; names never empty.
    slugs = [job.slug for job in jobs]
    assert len(slugs) == len(set(slugs))
    assert all(job.company_name for job in jobs)


def test_parser_extracts_structure_not_just_titles():
    _skip_if_no_corpus()
    jobs = parse_careers_file(str(CORPUS))
    assert all(job.description for job in jobs)
    assert all(job.summary for job in jobs)
    assert all(job.salary_min is not None and job.salary_max is not None for job in jobs)
    assert all(job.currency for job in jobs)
    assert any(job.requirements for job in jobs)


def test_import_is_idempotent_and_provenance_marked(db):
    _skip_if_no_corpus()
    jobs = parse_careers_file(str(CORPUS))[:5]

    first = import_jobs(db, jobs)
    assert first["created_jobs"] == 5
    assert first["created_opportunities"] == 5
    assert first["skipped"] == 0

    second = import_jobs(db, jobs)
    assert second["created_jobs"] == 0
    assert second["existing"] == 5

    postings = db.query(JobPosting).all()
    assert len(postings) == 5
    assert all(p.status == "published" for p in postings)
    assert all(p.imported_from and p.imported_from.startswith("careers:") for p in postings)
    assert all(p.opportunity_id for p in postings)

    opps = db.query(Opportunity).filter(
        Opportunity.source == "careers_compat"
    ).all()
    assert len(opps) == 5
    assert all(o.status == "active" for o in opps)

    org = db.query(Organization).filter(
        Organization.slug == "careers-corpus-imports"
    ).first()
    assert org is not None
    assert all(p.organization_id == org.id for p in postings)
