"""Aggregate router for /api/v1."""
from fastapi import APIRouter

from app.api.v1 import auth, consents, documents, organizations, workid

router = APIRouter()
router.include_router(auth.router)
router.include_router(organizations.router)
router.include_router(workid.router)
router.include_router(consents.router, prefix="/work-id")
router.include_router(documents.router)
