"""Centralized, environment-driven configuration for the canonical backend.

Secrets are never hardcoded here. Values come from environment variables
(optionally loaded from a ``.env`` file next to the working directory).
Fail-fast rules prevent accidental use of development defaults in
staging/production.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Values that must never be treated as real secrets in non-dev environments.
_INSECURE_SECRET_VALUES = {
    "",
    "dev-only-insecure-secret-do-not-use",
    "your-secret-key-here-change-me",
    "change-me",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AskTrabaajo Core API"
    app_version: str = "0.3.0"

    # development | test | staging | production
    environment: str = "development"

    api_v1_prefix: str = "/api/v1"

    # Canonical database. Default is a local sqlite dev database — never used
    # in staging/production (validated below).
    database_url: str = "sqlite:///./asktrabaajo_core.db"

    # JWT signing secret. REQUIRED in staging/production (fail-fast).
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30

    # Comma-separated list of allowed CORS origins.
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # Optional dev-only demo user (env-provided, never committed values).
    demo_user_email: str = ""
    demo_user_password: str = ""

    # Interview scheduling policy: small, configurable number of candidate
    # reschedules per interview (product principle: limited rescheduling).
    max_reschedules_per_interview: int = 2

    # Talent outreach abuse controls (Phase 8): a request expires if the
    # candidate has not responded within ``outreach_expiry_days``, and an
    # organization cannot send another request to the same candidate within
    # ``outreach_cooldown_days`` of the previous one (regardless of outcome).
    outreach_expiry_days: int = 30
    outreach_cooldown_days: int = 7

    # Rate limiting (Phase 9): enforcement toggle + store backend.
    # ``memory`` is the development/test implementation; ``db`` is the
    # multi-instance-safe backend over ``rate_limit_hits`` (Redis can replace
    # the store later without changing the policy layer).
    rate_limits_enabled: bool = True
    rate_limit_store: str = "memory"

    # PostgreSQL RLS session context (Phase 13): when True, every request
    # sets ``app.current_user_id`` / ``app.current_org_ids`` on its database
    # session from the authenticated actor and resets them on close, so
    # database-level RLS policies (defense in depth) see the canonical
    # identity. Only meaningful on PostgreSQL (SQLite is unaffected); the
    # app must connect as the least-privilege ``asktrabaajo_app`` role for
    # policies to take effect (owner/superuser roles bypass RLS).
    rls_session_context: bool = False

    # --- Athena AI core (Phase 14) -------------------------------------------
    # Provider selection is configuration-driven; ``none`` is the safe
    # default (Athena degrades to a clear AI_PROVIDER_UNAVAILABLE error —
    # it never fabricates responses). ``openai`` requires OPENAI_API_KEY.
    ai_provider: str = "none"
    # Server-side provider credential (env-injected; never logged).
    openai_api_key: str = ""
    ai_openai_model: str = "gpt-4o-mini"
    # Maximum provider-tool loop iterations per user message (bounded).
    ai_chat_max_turns: int = 3
    # Sanitized message retention (days). A purge job is a later
    # operational concern; the setting documents the policy now.
    ai_message_retention_days: int = 90
    # Session / confirmation lifetimes (minutes) — lazy expiry, no
    # scheduler dependency.
    athena_session_ttl_minutes: int = 60
    athena_confirmation_ttl_minutes: int = 15
    # Daily usage budgets per user (over the canonical ai_usage_log).
    athena_daily_messages_per_user: int = 100
    athena_daily_tool_calls_per_user: int = 200

    # --- AI Interview Engine media (Phase 16) ----------------------------------
    # Provider-neutral STT/TTS selection. ``none`` is the safe default:
    # voice stays disabled and media calls fail with ai.media_unavailable
    # (never a fabricated transcript or audio). ``mock`` is test-only.
    ai_stt_provider: str = "none"
    ai_tts_provider: str = "none"

    @field_validator("ai_provider")
    @classmethod
    def _ai_provider_allowed(cls, v: str) -> str:
        if v not in {"none", "openai"}:
            raise ValueError(f"ai_provider must be one of {{'none','openai'}}, got {v!r}")
        return v

    @field_validator("rls_session_context")
    @classmethod
    def _rls_context_requires_postgres(cls, v: bool, info) -> bool:
        environment = info.data.get("environment", "development")
        if v and environment in {"staging", "production"}:
            database_url = info.data.get("database_url", "")
            if database_url.startswith("sqlite"):
                raise ValueError(
                    "RLS_SESSION_CONTEXT requires a PostgreSQL DATABASE_URL in "
                    f"{environment}; sqlite cannot carry database-level RLS."
                )
        return v

    @property
    def is_production_like(self) -> bool:
        return self.environment in {"staging", "production"}

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @field_validator("environment")
    @classmethod
    def _environment_allowed(cls, v: str) -> str:
        allowed = {"development", "test", "staging", "production"}
        if v not in allowed:
            raise ValueError(
                f"environment must be one of {sorted(allowed)}, got {v!r}"
            )
        return v

    @field_validator("secret_key")
    @classmethod
    def _secret_key_safe(cls, v: str, info) -> str:
        environment = info.data.get("environment", "development")
        if environment in {"staging", "production"} and v in _INSECURE_SECRET_VALUES:
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in "
                f"{environment}; refusing to start with an insecure default."
            )
        if not v:
            return "dev-only-insecure-secret-do-not-use"
        return v

    @field_validator("database_url")
    @classmethod
    def _database_url_safe(cls, v: str, info) -> str:
        environment = info.data.get("environment", "development")
        if environment in {"staging", "production"}:
            if v.startswith("sqlite"):
                raise ValueError(
                    "sqlite database URLs are not allowed in "
                    f"{environment}; set DATABASE_URL to PostgreSQL."
                )
            if "postgres" not in v:
                raise ValueError("DATABASE_URL must point at PostgreSQL.")
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def is_url_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
