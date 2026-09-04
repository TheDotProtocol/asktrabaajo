# PHASE 12 — PRODUCTION INFRASTRUCTURE & STAGING FOUNDATION

This document records the infrastructure work performed in Phase 12 and
the design for staging/production. It is honest about what is READY,
NOT READY, and REQUIRES EXTERNAL INFRASTRUCTURE. Nothing in this phase
touched a shared/production database or deployed anything.

---

## 1. Deployment stack

### What changed (committed)

- **`docker-compose.yml` — hardened and made bootable.**
  - Every secret is now env-driven. The previous file hardcoded four
    secrets: a Postgres password (`secure_password_2024`), a backend
    `SECRET_KEY`, a Grafana admin password, and a DB URL embedding the
    password. These are gone; required values use
    `${VAR:?...}` fail-fast interpolation.
  - Removed services/mounts that referenced artifacts that do not exist
    in the repository and made `docker compose up` fail:
    - `frontend` service (no `frontend/Dockerfile`; the frontend deploys
      via Vercel per DEPLOYMENT_GUIDE.md).
    - `prometheus`/`grafana` services (no `monitoring/prometheus.yml`).
    - `nginx` edge (no `nginx/ssl` certificates; TLS terminates at the
      hosting edge/CDN).
    - `init.sql` mount (no file).
  - Added healthchecks: `pg_isready` for Postgres, `redis-cli ping` for
    Redis, and the existing `/health` probe for the backend, wired with
    `depends_on: condition: service_healthy`.
  - The backend service now runs the **canonical** FastAPI app
    (`uvicorn app.main:app`) — the image default CMD targets the legacy
    MVP app. Config fail-fasts (`SECRET_KEY`, `DATABASE_URL`) mirror the
    canonical app's own validation.
  - The stack is intentionally minimal: `postgres`, `redis`, `backend`.
    For hosted PostgreSQL (Supabase), skip the `postgres` service and
    point `DATABASE_URL` at the managed instance.
- **`docker-compose.env.example` (new)** — variable names only; copy to
  `.env`, never commit real values (`.env` is gitignored).
- Validated with `docker compose config` (syntax + interpolation) — PASS.

### NOT changed (and why)

- `backend/Dockerfile` — legacy-compatible image; builds (contains the
  canonical `app/` tree too). Image build/slim-down is deferred.
- `nginx/nginx.conf` — legacy artifact for the old VM deployment; kept
  untouched for compatibility. A containerized TLS edge is not needed
  while Vercel/edge terminates TLS.
- `scripts/deploy.sh`, `configure-domain.sh`, `setup-ssl.sh` — legacy
  deployment helpers; left as-is.

## 2. Environment configuration & secret management

- Canonical settings live in `backend/app/core/config.py` (env-driven,
  fail-fast in staging/production: rejects sqlite DATABASE_URL and
  insecure SECRET_KEY).
- `.env.example` templates exist for backend and frontend (names only).
- **Current posture:** staging/production deployment requires a real
  `DATABASE_URL` (PostgreSQL) and `SECRET_KEY`. No real secrets are
  committed anywhere (Phase 1 de-tracked `.env` files and sanitized
  docs; `docker-compose.yml` was the last hardcoded-secret artifact and
  is now fixed).
- **REQUIRES OWNER ACTION (blocker, carried from Phase 1):** the
  Supabase anon key, service-role key, DB password, SMTP password,
  OpenAI key, JWT secret and exposed crypto wallets are still
  known-exposed and must be rotated before any live staging work.

## 3. Health checks, startup/shutdown, connection handling

Present in the canonical app:

- `/health` liveness (no dependencies) and `/health/ready` readiness
  (DB `SELECT 1`, 503 on failure) — `backend/app/api/health.py`.
- `pool_pre_ping` on the SQLAlchemy engine; `NullPool` in migrations.
- Request-context middleware: `X-Request-ID` (in/out), client IP from
  `X-Forwarded-For`, user-agent, duration, access log line.
- Centralized exception handlers (`app/core/errors.py`).

Deferred (documented, not built):

- Connection **pooling tuning** for high concurrency (pool_size /
  max_overflow / queue) — the current defaults are fine for staging;
  tune against staged load.
- Graceful-shutdown drain hooks beyond FastAPI/uvicorn defaults.
- Trusted-hosts / proxy-headers middleware hardening (trust the hosting
  edge) — needed at deploy time, not before.

## 4. Staging database strategy

Target ladder:

```
Development ──► Local PostgreSQL / test SQLite ──► Staging Supabase PostgreSQL ──► Production Supabase PostgreSQL
```

Rules:

1. All schema changes are migration-driven (Alembic `0001`–`0009`,
   head `0009`). No dashboard edits, ever.
2. Staging is a **separate Supabase project** (or a dedicated DB/role in
   a staging host) — never the production project `zrvrjqwboylvvzusorry`.
3. SQLite is dev/test only; the app refuses it in staging/production.
4. Phase 11 proved migrations `0001`–`0009` + enforcement/appeal flows
   against a local PostgreSQL 16; this is the repeatable staging script:
   - `createdb` a scratch DB on the staging host,
   - `alembic upgrade head`,
   - boot the app, run the canonical test suite against it,
   - representative API flows (auth, Work ID, application, talent,
     outreach, communication, governance, enforcement, appeals),
   - `alembic downgrade -1` + `upgrade head` to prove reversibility.

**Status:** local-PG validation READY (proven in Phase 11); real
staging-Supabase validation REQUIRES EXTERNAL INFRASTRUCTURE (a staging
project + rotated credentials, owner action). The exact command/checklist
is in §9.

## 5. RLS enablement design (PostgreSQL defense in depth)

Prepared, NOT applied — nothing was enabled on any database.

Design:

1. **Roles:** a superuser (once) creates `asktrabaajo_app` — a
   non-owner role granted only what the app needs (`CONNECT`, `USAGE`,
   `SELECT/INSERT/UPDATE/DELETE` on canonical tables, `USAGE` on
   sequences) — plus a privileged migration role. Never run the app as
   the table owner.
2. **Session marker:** the app sets `app.current_user_id` and
   `app.current_org_ids` (comma-separated) per transaction from the
   authenticated actor — never from client input. The Phase 9 artifact
   `backend/app/db/rls.py` defines the policy families (org-scoped,
   person-scoped, indirect-via-parent) and the coverage test.
3. **Staged enablement:** enable RLS per table group in order, verifying
   API + DB isolation after each group:
   a. person-scoped high-value: `conversations`/`messages`,
      `job_applications`, `person_documents`, `credentials`,
      `outreach_requests`; then
   b. org-scoped: `company_profiles`, `job_postings`, `talent_pools`,
      `saved_candidates`, `memberships`; then
   c. governance/enforcement/appeals (platform-scope — these are NOT
      org-tenant rows and need platform-role policies, not tenant ones).
4. **Owner-bypass caveat:** table owners (incl. the Postgres superuser)
   bypass RLS. Phase 11 proved the semantics (non-owner role saw exactly
   its tenant's rows: 1/1/2/0 across session markers). Deployment must
   use the non-owner app role; this is documented, not hidden.
5. Application-level authorization remains **mandatory**; RLS is
   defense in depth.

**Status:** design + semantics validated on local PG 16 (Phase 11);
production enablement REQUIRES EXTERNAL INFRASTRUCTURE (staging project,
app role, session-marker wiring at deploy) and is a later, guarded
migration — never a blind `ALTER TABLE ... ENABLE RLS` sweep.

## 6. Backups & recovery (design; not configured anywhere)

- **Production (Supabase):** managed PITR — assume the Supabase PITR
  window with scheduled backups enabled, and a staging restore process
  (restore a PITR copy into the staging project).
- **Staging:** nightly `pg_dump -Fc` + periodic restore test.
- **Migration rollback:** every canonical migration has a downgrade;
  practice is `downgrade -1 → upgrade head` on scratch before deploying
  forward.
- **Restore testing:** restore-the-backup is the only valid test — a
  quarterly restore drill on staging is required before production
  readiness can be claimed.
- **Disaster recovery assumptions:** hosting-edge managed TLS + managed
  DB; the app is stateless (no local files beyond logs), so a restore +
  redeploy rebuilds the system.
- **Status:** DESIGN ONLY. No backup/restore capability is configured or
  tested; nothing production-ready is claimed.

## 7. Observability

Present: structured access logs with request IDs; audit system with
correlation IDs; `/health` + `/health/ready`; rate-limit and audit
records in the DB.

Required for production (foundation designed, not built):

- Structured JSON log output option + log-level config.
- Application metrics endpoint (request latency, error rate by route,
  auth failure counts, authorization failure counts, background job
  failures, notification failures, future AI/external integration
  failures).
- DB health/connection-pool metrics.
- Metric scraping contract (any provider-neutral exporter; Prometheus
  was removed from compose because its config was absent — the endpoint
  can be added to a scrape target later).

Sensitive-information rule (already enforced): no passwords, tokens,
message bodies, document contents, or personal data in logs — the Phase 9
audit-hygiene tests assert this.

**Status:** foundation READY; production metrics collection REQUIRES
EXTERNAL INFRASTRUCTURE.

## 8. Realtime design (production approach; not enabled)

Phase 9 built the canonical, authorization-aware event log
(`platform_events`, metadata-only payloads, user/org addressing) polled
via `/api/v1/events`; Phase 10 wired governance events; the frontend
communications centers poll with a live pulse.

Production approach when infrastructure exists:

1. Keep `platform_events` as the **source of truth** and the event
   contract.
2. Add a transport adapter (WebSocket or SSE, or managed realtime) that
   fans out events to exactly the recipients the event addressing
   already defines — the transport must not re-derive or bypass
   authorization.
3. Never broadcast full records; never include private Work ID /
   document / message-body content in events.
4. Enable per-channel subscriptions only after the session-marker RLS and
   app-role deployment exist (same dependency as §5).

**Status:** contract + server-side abstraction READY; production
transport REQUIRES EXTERNAL INFRASTRUCTURE (managed realtime or a
self-hosted gateway) — documented, not faked.

## 9. Staging validation checklist (exact commands)

Preconditions (owner actions, NOT performed):

- Rotate: Supabase anon + service-role keys, DB password, SMTP
  password, OpenAI key, JWT secret.
- Provision a staging Supabase project (or staging Postgres host).
- Provide `DATABASE_URL`, `SECRET_KEY` via a secrets manager/env.

Then:

```bash
# 1. Create the staging database (non-destructive, isolated)
createdb asktrabaajo_staging        # or create DB in staging Supabase project

# 2. Apply canonical migrations (staging only)
cd backend
ENVIRONMENT=staging DATABASE_URL="$STAGING_DB_URL" SECRET_KEY="$STAGING_SECRET" \
  .venv/bin/alembic upgrade head

# 3. Boot + health
ENVIRONMENT=staging DATABASE_URL="$STAGING_DB_URL" SECRET_KEY="$STAGING_SECRET" \
  .venv/bin/uvicorn app.main:app --port 8000 &
curl -fsS localhost:8000/health && curl -fsS localhost:8000/health/ready

# 4. Run the canonical suite against staging (test env, staging DB)
ENVIRONMENT=test DATABASE_URL="$STAGING_DB_URL" .venv/bin/python -m pytest tests_phase3 -q

# 5. Migration reversibility on staging
ENVIRONMENT=staging DATABASE_URL="$STAGING_DB_URL" SECRET_KEY="$STAGING_SECRET" \
  .venv/bin/alembic downgrade -1
ENVIRONMENT=staging DATABASE_URL="$STAGING_DB_URL" SECRET_KEY="$STAGING_SECRET" \
  .venv/bin/alembic upgrade head

# 6. RLS enablement (guarded, per table group — see §5) with app role
#    CREATE ROLE asktrabaajo_app ... (superuser, once)
#    then staged ALTER TABLE ... ENABLE ROW LEVEL SECURITY + policies

# 7. Container smoke (optional, local)
cd .. && cp docker-compose.env.example .env  # fill values
docker compose up -d && curl -fsS localhost:8000/health
```

**Status:** checklist READY; execution REQUIRES staging credentials +
rotation (owner action).

## 10. Frontend (Phase 12 scope)

No product-UI changes were made. The frontend's direct Supabase reads
(`lib/supabase.ts`, `lib/careers/*`) are the legacy compatibility path
for the live Careers platform and remain untouched. Environment templates
(`frontend/.env.example`) already exist. API/session plumbing for the
canonical app is a frontend workstream for a later phase.

## 11. Production readiness (honest status)

| Area | Status |
|---|---|
| Canonical app + migrations 0001–0009 | READY (validated on SQLite + local PG) |
| docker-compose stack | READY (bootable, secret-safe, healthchecked) |
| Staging DB validation | REQUIRES EXTERNAL INFRASTRUCTURE (credentials/rotation + staging project) |
| RLS enablement | REQUIRES EXTERNAL INFRASTRUCTURE (app role + staged enablement) |
| Realtime transport | REQUIRES EXTERNAL INFRASTRUCTURE |
| Observability (metrics/JSON logs) | NOT READY (foundation only) |
| Backups/restore drills | NOT READY (design only) |
| Secret rotation | BLOCKED ON OWNER (Phase 1 carry) |
| Production deployment | NOT READY — no deployment has been performed or claimed |

## 12. Deferred work (explicit)

- Image slim-down + frontend containerization (Vercel is the current
  path).
- Metrics endpoint + JSON log output.
- Backup/restore drills.
- Trusted-hosts/proxy middleware hardening at deploy time.
- Live read-only schema diff of the Supabase project (needs approved
  credentials).
- Supabase Auth/Storage cutover for the careers path (frontend
  workstream).