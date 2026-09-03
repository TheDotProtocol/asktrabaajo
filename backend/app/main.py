"""Canonical AskTrabaajo backend — app factory.

Legacy backend (``backend/main.py`` + ``backend/api``) is untouched and
remains the live service during the strangler migration. This app is the
future single authoritative API surface.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.ratelimit import build_limiters


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings)

    app = FastAPI(
        title="AskTrabaajo Core API",
        description=(
            "Canonical API for AskTrabaajo — The Operating System for Work. "
            "Foundation build (Phase 3)."
        ),
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    # In-process rate limiters from the policy registry (Phase 9). A
    # multi-instance deployment swaps the store for Redis/DB without changing
    # the policy layer.
    app.state.rate_limiters = build_limiters()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)

    app.include_router(health_router)
    app.include_router(v1_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {
            "service": "AskTrabaajo Core API",
            "version": __version__,
            "docs": "/api/docs",
        }

    return app


app = create_app()
