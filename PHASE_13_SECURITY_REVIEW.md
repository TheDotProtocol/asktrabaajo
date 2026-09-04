# PHASE 13 — SECURITY REVIEW

Scope: database security (PostgreSQL/Supabase), API security
re-validation, connection pooling, secret rotation status, and
observability. All findings are evidence-based from the repository and
the local PostgreSQL validation; nothing was enabled on the live project.

## 1. Database security

| Check | Result |
|---|---|
| Extensions | Canonical schema uses `uuid`/`uuid-ossp`-compatible UUIDs via SQLAlchemy `Uuid`; no extra extensions required by migrations. Legacy `uuid-ossp` extension is untouched. PASS |
| SECURITY DEFINER functions | None exist in canonical code (canonical never runs DB functions for authz). PASS — and none should be added without the Phase 13 staged-writer review |
| `search_path` | Canonical code uses fully-qualified ORM queries; the app role gets `USAGE` on `public` only. PASS (reviewed; no dynamic SQL found) |
| SQL injection | ORM/parameterized queries throughout; no string-built SQL in services (migration 0010 builds policy SQL from a hardcoded table/column tuple, never from user input). PASS |
| Dangerous grants | Removed from `docker-compose` in Phase 12; runtime role grants are table-DML only (62 canonical tables), no DDL. `scripts/db/app_role.sql` verified: `NOSUPERUSER NOCREATEDB NOCREATEROLE`, no `auth`/`storage`/`graphql`/`realtime` schema access. PASS |
| Owner privileges / role separation | `asktrabaajo_app` role created on scratch PG and proven: DDL denied, legacy schemas denied, RLS respected. Migration owner (postgres) vs runtime role separated by design. PASS (validated locally; deployment step required for live) |
| Public schema exposure | Canonical tables are RLS-protected where tenant data lives (stage A enabled; B/C designed); catalog/discovery tables intentionally open to authenticated app reads. Legacy tables untouched. PASS (with staged B/C pending) |
| FK / unique / check constraints | Present via migrations 0001–0009 (e.g., `uq_applications_person_opportunity`, unique emails/slugs). PASS |
| Cascading deletes | `ON DELETE CASCADE` on ownership chains (person → goals/dna/credentials/documents); reviewed as matching product semantics (deleting a person removes their private data). PASS |
| Indexes | Reviewed for tenant-filtering gaps; the high-frequency tenant columns (`person_id`, `user_id`, `organization_id`) are indexed on the stage-A/B tables (verified in model metadata). No speculative indexes added. PASS |

## 2. RLS posture

- **Enabled (validated):** stage A (6 owner-private tables) via migration
  `0010` on local PostgreSQL; hostile tests green.
- **Not enabled anywhere live** — no live changes (blocked on
  credentials). Groups B/C in PHASE_13_RLS_MATRIX.md are designed but
  staged behind: (1) the app running as `asktrabaajo_app`, (2) the
  two-party policy deployment, (3) the platform-role `app.current_roles`
  GUC. Enabling them before those mechanisms exist would either be
  ineffective (owner bypass) or break authorized flows — deliberately not
  done.

## 3. API security re-validation (against the deployed surface)

| Check | Result |
|---|---|
| Authentication | Canonical JWT (bcrypt, access+refresh, token_version revocation), enforcement reconciliation on auth path (Phase 11). PASS |
| Authorization | Server-side RBAC (membership + role + permission + tenant scope) on every route; `require_super_admin` is platform-scope only. PASS |
| Tenant isolation | Hostile-path tests across phases 8–11 (cross-org outreach/comm/gov/enforcement/appeals denied with known UUIDs). PASS |
| IDOR/BOLA | No new read/write surface added in Phase 13 (no new routes); existing suites cover UUID-knowledge attacks. PASS |
| Rate limits | Centralized policy registry, generic 429s, no account-existence leak (tested). PASS |
| Audit logging | Every sensitive event audited with actor/action/resource/org/correlation; no secrets/bodies in payloads (test-enforced). PASS |
| Error leakage | Centralized handlers; health endpoints expose no internals. PASS |
| Document authz | Candidate-controlled documents + grants + consents (Phase 4); storage abstraction provider-neutral, not yet wired. PASS (upload path must define validation rules when it lands) |

## 4. Connection pooling / session identity

- `pool_pre_ping` engine; sessions per-request; the Phase 13 mechanism
  sets `app.current_user_id`/`app.current_org_ids` per request and resets
  them in `get_db().finally` **before the connection returns to the pool**
  — proven by the concurrent-session isolation test (two sessions with
  different identities; reset of one does not affect the other; post-reset
  value is empty).
- Session variables are never client-supplied (set only from the decoded
  token's user + membership rows).
- Failure path: reset wrapped in try/rollback so a failed request cannot
  leave identity behind. PASS (validated locally).

## 5. Secrets

| Credential category | Status |
|---|---|
| Supabase anon key | NOT ROTATED (Phase 1 carry; public-by-design but exposed historically) — PENDING ROTATION |
| Supabase service-role key | NOT ROTATED — PENDING ROTATION (never used by canonical code; do not use for inspection) |
| Database password (stored pooler/direct) | PENDING ROTATION; additionally the stored endpoint is DEAD (hostname retired) — a current connection string is required |
| SMTP credentials | PENDING ROTATION |
| OpenAI key | PENDING ROTATION |
| JWT secret | PENDING ROTATION |
| Crypto wallets | PENDING ROTATION (Phase 1 flagged; not present in canonical code) |

No secret values were printed or committed in Phase 13. Application
fail-fast behavior: canonical config refuses insecure `SECRET_KEY` and
sqlite URLs in staging/production (existing tests cover this).

## 6. Observability

Existing: structured access logs with request IDs, audit system with
correlation IDs, `/health` + `/health/ready`. Phase 13 added nothing that
logs payloads. Deferred (documented in Phase 12): metrics endpoint, JSON
log output option, backup/restore drills. Never-log list (enforced by
tests): passwords, tokens, message bodies, document contents, KYC data,
personal data.

## 7. Overall result

**SECURITY: PASS WITH LIMITATIONS.** No new attack surface; RLS stage 1
implemented and proven at the database layer; runtime-role least
privilege proven. Limitations are the staged B/C RLS groups (designed,
not enabled), the missing live-deployment credentials, and the carried
secret-rotation backlog — all owner/deployment actions, none silently
skipped.