# AskTrabaajo — Phase 3 Foundation Report

**Date:** 2026-09-03 · **Phase 3 of the v2.0 rebuild** · Scope: canonical platform foundation (first implementation phase).

**Status:** complete per the Phase 3 definition of done. The careers platform and legacy backend are untouched and remain the live system; this foundation runs beside them (strangler migration).

**Companion documents:** `AUDIT_REPORT.md` · `PHASE_1_REPORT.md` · `PHASE_2_ARCHITECTURE.md` (approved blueprint — this phase implements P3/P4-skeleton/P5-skeleton/P6-skeleton of §25 in foundation form).

---

## 1. What was created

### 1.1 Canonical backend — `backend/app/`

One authoritative FastAPI package. It does **not** import from the legacy `backend/api` tree and the legacy tree does not import it — both coexist.

```
backend/app/
├── __init__.py               version 0.3.0
├── main.py                   create_app() factory; module-level app
├── core/
│   ├── config.py             pydantic-settings, env-driven, fail-fast (§2)
│   ├── errors.py             uniform error envelope + handlers
│   ├── security.py           bcrypt hashing, JWT access tokens, token hashing
│   ├── logging.py            structured logging w/ request-id injection
│   ├── middleware.py         request-id + client metadata + access log
│   ├── context.py            per-request context (contextvars)
│   └── timeutil.py           UTC helpers (SQLite↔PostgreSQL safe)
├── db/
│   ├── base.py               DeclarativeBase + naming convention
│   └── session.py            engine/session from settings (no auto-create_all)
├── models/                   canonical ORM (ONE model set, UUID ids)
│   ├── identity.py           users · person_profiles · refresh_tokens
│   ├── tenancy.py            organizations · memberships · roles · permissions
│   │                         · role_permissions
│   ├── work.py               work_experiences · educations · skills ·
│   │                         user_skills · credentials · employments
│   ├── documents.py          person_documents · document_access_grants
│   ├── audit.py              audit_log (append-only)
│   ├── catalog.py            role/permission seed catalog + idempotent seeding
│   └── enums.py              shared value constants
├── schemas/                  Pydantic v2 request/response contracts (auth,
│                             tenancy, work, documents, common)
├── services/
│   ├── auth_service.py       register/login/token pairs/refresh rotation
│   ├── authz.py              membership + permission checks (RBAC core)
│   ├── tenancy.py            org creation + membership management
│   ├── document_access.py    controlled document access + grants
│   └── audit.py              single reusable audit writer
└── api/
    ├── deps.py               get_current_user, require_org_permission,
    │                         require_super_admin
    ├── health.py             /health, /health/ready
    └── v1/                   versioned routers: auth · organizations ·
                              workid · documents (+ aggregate router)
```

### 1.2 Migration tooling — `backend/alembic/`

- `alembic.ini` + `alembic/env.py` (URL resolved from centralized settings, never hardcoded) + `script.py.mako`.
- **Initial revision `0001` — strictly additive**: 17 new tables (`users`, `person_profiles`, `refresh_tokens`, `organizations`, `memberships`, `roles`, `permissions`, `role_permissions`, `work_experiences`, `educations`, `skills`, `user_skills`, `credentials`, `employments`, `person_documents`, `document_access_grants`, `audit_log`) + role/permission catalog seed rows.
- None of these tables exist in the live Supabase schema → zero collision, zero destructive change.
- Validated locally: `upgrade head` → downgrade → re-upgrade on a scratch SQLite DB (17 tables, 11 roles, 21 permissions, 43 mappings). **No migration was run against any shared or production database.**

### 1.3 Configuration & hygiene

- `backend/.env.example` and `frontend/.env.example` — **variable names only**, no values.
- Fail-fast validation: staging/production refuse insecure/missing `SECRET_KEY` and any non-PostgreSQL `DATABASE_URL`.
- `requirements.txt`: added `alembic==1.16.5`. Dev venv additions: `pytest 8.2.2`, `alembic 1.16.5`, and `httpx` pinned to `0.25.2` (0.28 is incompatible with Starlette's TestClient — pre-existing dependency trap documented).

### 1.4 Test foundation — `backend/tests_phase3/`

- Isolated harness (`conftest.py`): forces `ENVIRONMENT=test` + `DATABASE_URL=sqlite://` **before any application import** so pytest can never reach a real database (Phase-1 hazard eliminated). Each test gets a fresh in-memory DB with the full canonical schema + seeded catalog; SQLite foreign keys are enforced.
- `pytest.ini` (per-suite config, avoids the legacy `--cov` addopts).
- Suites: config safety, auth, authorization/tenancy (Phase-1 regressions), work-id isolation, document access, error envelope/health, audit coverage, **ORM↔migration schema parity**.

## 2. What was migrated

Nothing was migrated from the legacy system. Phase 3 builds the foundation *alongside* it. Legacy routes, models, frontend flows, and the careers platform are unchanged (verified: legacy `main.py` still imports; careers frontend untouched).

## 3. What was NOT migrated / built (explicit)

- ❌ No legacy route or model consolidation (`api/` vs `backend/api/` untouched; `simple_database` vs `database` untouched).
- ❌ No jobs/companies-mirror models — the live careers `companies`/`jobs`/`applications` tables are deliberately **not** claimed by the canonical schema yet (P4/P7).
- ❌ No Supabase Auth migration (documented UNKNOWN — P5 spike).
- ❌ No frontend page migration — the API client boundary exists but no page uses it yet.
- ❌ No interviews, payments, government intelligence, Athena, AI, blockchain.
- ❌ No destructive migration; no production/shared database touched; no secrets introduced.

## 4. Database changes

| Item | Value |
|---|---|
| New tables (additive only) | 17 foundation tables (listed in §1.2) |
| Existing tables touched | **none** |
| Migrations generated | 1 (`0001`) |
| Migrations applied to shared/prod DB | **none** |
| Migration validated | scratch SQLite upgrade→downgrade→upgrade ✅ |
| Rollback | `alembic downgrade base` drops only the 17 new tables + seed rows (zero data-loss risk to pre-existing data) |
| Test-DB isolation | in-memory SQLite per test; env forced before imports |

## 5. API changes — endpoints created (all under `/api/v1`)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health`, `/health/ready` | none | liveness / readiness (DB ping) |
| POST | `/auth/register` | none | create account + person profile |
| POST | `/auth/login` | none | credential login |
| POST | `/auth/refresh` | none (refresh token) | rotate refresh token (reuse = family revocation) |
| POST | `/auth/logout` | none (refresh token) | revoke refresh token |
| GET | `/auth/me` | bearer | user + person + memberships + effective permissions |
| POST | `/organizations` | bearer | create org (creator becomes org_admin; platform/government orgs = super-admin only) |
| GET | `/organizations` | bearer | my organizations |
| GET | `/organizations/{id}` | member | read org |
| POST | `/organizations/{id}/members` | members.manage | add member (role scope validated) |
| GET | `/organizations/{id}/members` | members.read | list members |
| PATCH | `/organizations/{id}/members/{user}` | members.manage | change role (last-admin guard) |
| DELETE | `/organizations/{id}/members/{user}` | members.manage | remove member (last-admin guard) |
| GET | `/work-id` | owner | full Work ID summary |
| PUT | `/work-id/profile` | owner | update person profile |
| GET/POST | `/work-id/experiences`, `/educations`, `/employments` | owner | list/create |
| PATCH/DELETE | `…/{id}` (experiences/educations) | owner | update/delete (ownership = 404 for others) |
| GET/POST | `/work-id/credentials` | owner | list/create (status starts `unverified`) |
| PATCH/DELETE | `/work-id/credentials/{id}` | owner | update (verification fields not settable) / delete |
| GET/PUT/DELETE | `/work-id/skills` | owner | own skills (auto-create catalog entries) |
| GET/POST | `/documents` | owner | list/create own document metadata |
| GET | `/documents/{id}` | owner or live grant | fetch (denied attempts → 404 + audit) |
| DELETE | `/documents/{id}` | owner | archive |
| GET/POST | `/documents/{id}/grants`, DELETE `…/grants/{grant}` | owner | manage access grants (user or org, expiry, revocation) |

No legacy routes were recreated speculatively. Error responses use one machine-readable envelope: `{"error": {"code", "message", "details"}}`.

## 6. Authentication changes

- Canonical auth is FastAPI-owned: bcrypt hashing, 15-min JWT access tokens with typed claims (`sub`, `type`, `token_version`, `jti`, `iat`, `exp`), opaque refresh tokens stored **hashed** with rotation; reuse of a rotated token revokes the whole token family; logout revokes; `token_version` supports whole-session invalidation.
- No plaintext passwords anywhere; no admin password-view capability exists.
- Supabase Auth is untouched and still serves the live frontend — migration mechanics remain **UNKNOWN** (P5 spike, per Phase 2 §7.1).

## 7. Authorization model

- `permission = domain:action`; `role = permission set`; `membership = user + org + role`; enforcement = membership lookup + role permissions + organization scope.
- Roles seeded: platform (`super_admin`, `customer_support`, `tech_support`, `marketing`, `finance`), organization (`org_admin`, `hr`, `recruiter`, `hiring_manager`), government (`government_admin`, `government_user`) with 21 permissions.
- **Super admin is platform-scope only**: it exists solely as a membership in a platform-kind organization; platform/government orgs can be created only by platform super admins; role scope is validated against org kind so `super_admin` can never be planted inside an employer org.
- The Phase-1 flaw (`employer ⇒ super admin`) is structurally impossible in the canonical model and is covered by regression tests.

## 8. Testing results

| Suite | Result |
|---|---|
| Canonical `tests_phase3` (48 tests: config safety, auth, authz/tenancy regressions, work-id isolation, document access, error/health, audit, schema parity) | **48 passed** ✅ |
| Legacy suite `backend/tests` (safely, sqlite override) | **BLOCKED (pre-existing)** — fails at collection: `cannot import name 'seed_test_user'` from `api.models.database`; unrelated to Phase 3; never reaches any DB |
| Legacy backend import (`import main`, 107 routes) | ✅ unchanged |
| Frontend typecheck (`tsc --noEmit`) after boundary files | ✅ 0 errors |

Regression tests for the security brief (§16/§23) — all passing:
- employer/company cannot reach platform admin; cannot create platform or government orgs ❌→403
- Company A cannot read/manage Company B (org read, member list, member add, role change) ❌→403
- HR cannot manage memberships (members.manage/read denied) ❌→403
- non-member org read → 403; unauthorized document fetch → 404 + `document.access.denied` audit
- last-org-admin downgrade/removal refused
- cross-user Work ID access → 404 (existence hidden)
- government members hold no individual-data permissions

## 9. Security controls delivered

Config fail-fast (no insecure secret defaults in staging/production; Postgres-only there) · bcrypt + typed short-lived JWTs + hashed rotating refresh tokens + reuse detection · permission registry enforcement on every gated endpoint · tenant-scoped membership checks · document grants with expiry/revocation + audited denials · append-only audit design with request metadata · structured logging with request id (no secrets logged) · uniform safe error envelope (no stack traces/credentials) · CORS env-driven · health endpoints leak nothing.

## 10. Careers compatibility

- Careers platform (frontend + Supabase data + seeds) untouched — no shared file changed.
- Canonical tables are all new names; no `create_all` runs anywhere in the canonical app (schema comes from Alembic only), so the live Supabase schema cannot be accidentally mutated.
- Legacy backend still imports and is unchanged; the legacy-safe pytest config documents how to run the legacy suite against a throwaway DB during the migration.

## 11. Known limitations

- Access tokens are not individually revocable pre-expiry (whole-session `token_version` only); fine for foundation.
- No email verification / MFA / password reset UI yet (P5 scope); user `email_verified` is structural only.
- Rate limiting is documented for P5 (not yet in canonical app; nginx covers the legacy Docker path).
- Audit "append-only" is enforced by application convention; DB-level write protection needs the dedicated least-privilege role (P4).
- Roles/permissions catalogs are seeds (migration + tests); admin UI to manage them comes with Super Admin (P14).
- Test DB is SQLite — parity with PostgreSQL column semantics is covered by the migration parity test and Postgres validation is scheduled for staging (P4).
- Frontend API boundary is infrastructure-only; no page wiring yet (deliberate).

## 12. Commands

```bash
# run the canonical suite (isolated; never touches a real DB)
cd backend && ./.venv/bin/python -m pytest -c tests_phase3/pytest.ini tests_phase3

# run the LEGACY suite safely (throwaway DB only)
cd backend && DATABASE_URL="sqlite:////tmp/legacy_safe.db" \
    ./.venv/bin/python -m pytest -c pytest.legacy-safe.ini tests

# inspect/validate the additive migration on a scratch DB (NOT against live)
cd backend && DATABASE_URL="sqlite:////tmp/scratch.db" ./.venv/bin/alembic upgrade head

# apply migrations to a real target later (staging/production — after review)
# cd backend && alembic upgrade head   # target chosen by DATABASE_URL
```

## 13. Files created/modified

**Created:** `backend/app/**` (42 Python files) · `backend/alembic/**` · `backend/alembic.ini` · `backend/tests_phase3/**` (10 files) · `backend/pytest.legacy-safe.ini` · `backend/.env.example` · `frontend/.env.example` · `frontend/src/lib/api/{client,types}.ts` · `PHASE_3_FOUNDATION.md`.
**Modified:** `backend/requirements.txt` (added alembic pin).

*End of Phase 3. No Phase 4 work has begun. Next: owner review, then the Phase 4 data layer per PHASE_2_ARCHITECTURE.md §25.*
