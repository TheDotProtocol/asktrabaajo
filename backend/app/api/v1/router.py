"""Aggregate router for /api/v1."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    company,
    consents,
    documents,
    enforcement,
    events,
    governance,
    jobseeker,
    organizations,
    talent,
    workid,
)

router = APIRouter()
router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(workid.router)
router.include_router(consents.router, prefix="/work-id")
router.include_router(documents.router)
router.include_router(jobseeker.router)
router.include_router(company.router)
router.include_router(talent.router)
router.include_router(governance.router)
router.include_router(enforcement.router)
router.include_router(events.router)
