"""Safe health/diagnostics endpoints.

- ``/health``       liveness — process is alive (no dependencies touched)
- ``/health/ready`` readiness — DB reachable (503 when it is not)

No secrets or infrastructure details are ever exposed.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "asktrabaajo-core", "version": __version__}


@router.get("/health/ready")
def health_ready(db: Session = Depends(get_db)) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "database_unavailable"},
        )
    return JSONResponse(
        status_code=200, content={"status": "ready", "database": "reachable"}
    )
