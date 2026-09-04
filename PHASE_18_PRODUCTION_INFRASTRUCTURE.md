# Phase 18 — Production Infrastructure

## Runtime topology (as-designed)

```
[ Next.js frontend ] ──HTTPS──▶ [ Canonical backend  :8000/api/v1 ] ──▶ Supabase
                                  │                                     │
                            (asktrabaajo_app,            (project zrvrjqwboylvvzusorry)
                             RLS_SESSION_CONTEXT=1)
                                                                     ├── legacy public domain (REST/anon)
                                                                     ├── canonical domain (80 tables, RLS)
                                                                     └── storage (3 private buckets)
```

- **Frontend:** Next.js app under `frontend/`; build manifest covers `/jobseeker/ai-interview`, `/employer/ai-interviews`, `/employer/billing` and all core routes. Typecheck/lint/build green this phase.
- **Backend:** canonical FastAPI app (`backend/app/main.py`, 246 `/api/v1` routes). Legacy backend (`backend/main.py`, 107 routes) is separate and preserved.
- **Database:** Supabase session pooler (port 5432), PostgreSQL 17.6. Alembic + SQLAlchemy. No live migration applied yet (gated).
- **Docker:** `docker-compose.yml` + `docker-compose.env.example` exist; deploy runbook from earlier phases (`DEPLOYMENT_GUIDE.md`, `railway-setup.md`) — must be reconciled with the live DB plan before use.

## Environment configuration

Config lives in `backend/app/core/config.py` (pydantic-settings, `.env`-loaded). Production-relevant switches:

| Setting | Production value to set | Note |
|---|---|---|
| `ENVIRONMENT` | `staging` / `production` | Fail-fast validators activate |
| `DATABASE_URL` | Supabase pooler URL | In `backend/.env` (gitignored) |
| `SECRET_KEY` | strong random | Refuses insecure defaults in non-dev |
| `CORS_ORIGINS` | real frontend origins | Default is localhost-only |
| `RLS_SESSION_CONTEXT` | `1` | Requires PostgreSQL + app role |
| `RATE_LIMIT_STORE` | `db` (or Redis) | **Multi-instance blocker** otherwise |
| `AI_PROVIDER` | `openai` + `OPENAI_API_KEY` | Only when provisioned |
| `PAYMENT_PROVIDER` | `mock` until a production provider is approved | `stripe` requires secret; not wired |
| `AI_STT_PROVIDER` / `AI_TTS_PROVIDER` | provider value only when provisioned | `none` = disabled (safe) |

## Environment inventory (production checkboxes)

- TLS: nginx + `setup-ssl.sh` exist for the site; verify certs + redirect for API domain.
- Health: canonical `GET /health` and `/api/v1/...health`; verify in the runbook load-balancer.
- Logging: structured logs exist; never log secrets, DATABASE_URL, tokens, CVV (observability doc).
- Secrets: none in Git/images/bundles/docs; scan clean.

## Readiness statement

The canonical platform is **development ready** and the reconciliation plan is validated. The platform is **not yet production ready** until the gated live bootstrap, distributed rate limiting, real CORS/origins for the API domain, TLS, and provider provisioning (AI/payment/email/voice) are completed and verified. See `PHASE_18_LAUNCH_CHECKLIST.md`.
