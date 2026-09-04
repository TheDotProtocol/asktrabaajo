# Phase 19 — Staging Architecture

## Status

**STAGING: LOCAL VALIDATION PASS / REMOTE STAGING INFRASTRUCTURE BLOCKED** — no separate staging Supabase project or remote environment exists, and the phase forbids creating one automatically without owner authorization. A genuine staging environment was demonstrated locally in `ENVIRONMENT=staging` mode against scratch PostgreSQL 16 at migration 0014.

## Target architecture (operator-decision required)

```
                    INTERNET
                       │ HTTPS
                STAGING FRONTEND (Next.js)
                       │
                 STAGING API (canonical FastAPI, ENVIRONMENT=staging)
                       │
              ┌────────┴────────┐
              │                 │
          SUPABASE DB       SERVICES
      (isolated staging       AI / payment (mock/sandbox) /
       project or schema)     email / voice-video
              │
             RLS
```

Options for the staging database (operator decision — none chosen, none created):

1. **Separate Supabase project** (recommended) — genuinely isolated, safe restore testing, clean synthetic data.
2. **Separate database in the same project** — lighter, but shares project-level backup/RLS/storage config.
3. **Isolated schema** — not recommended: shares the pooler role surface and complicates RLS/search_path.

## Staging configuration (what the canonical app needs)

| Setting | Staging value |
|---|---|
| `ENVIRONMENT` | `staging` (activates fail-fast secret/DB validators) |
| `DATABASE_URL` | staging DB URL (never the production project unless it IS the target) |
| `SECRET_KEY` | dedicated strong random value |
| `CORS_ORIGINS` | staging frontend origin |
| `RLS_SESSION_CONTEXT` | `1` (PostgreSQL required) |
| `RATE_LIMIT_STORE` | `db` (multi-instance-safe) |
| `AI_PROVIDER` | configured provider or `none` |
| `PAYMENT_PROVIDER` | `mock` (real money impossible) |
| `AI_STT/TTS_PROVIDER` | provider or `none` (disabled) |

**Never** point staging at the production project unnecessarily, and never reuse production secrets.

## What was validated locally (this phase)

`P19_STAGING_SMOKE_PASS` — the canonical app booted with `ENVIRONMENT=staging` (env-var override; `backend/.env` untouched) against scratch PG 16 and passed the full journey:

- Auth (register/login tokens), health/readiness
- Org + opportunity tenant anchor
- AI interview end-to-end: create → invite → claim → consent → start → question → answer → complete → report → **human decision** (advance)
- Commerce self-service (billing read) + **finance RBAC boundary (403)**
- **Cross-tenant denial (403)** — candidate cannot read employer report

This demonstrates the staging configuration contract works before any remote staging infra is provisioned.