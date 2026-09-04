# PHASE 12 — SECURITY REVIEW

Scope: the security gates listed in the Phase 12 brief, applied to the
repository as it exists on disk. This review is **read-only** — it found
and (where in-scope) fixed issues, and it records findings that require
owner action. Nothing was weakened to make tests pass.

---

## 1. Secrets

**Finding F12-1 (FIXED in this phase):** `docker-compose.yml` hardcoded
four secrets — a Postgres password, a database URL embedding it, a
backend `SECRET_KEY`, and a Grafana admin password. All are now
env-driven with fail-fast interpolation (`${VAR:?...}`); a
`docker-compose.env.example` documents the names only.

**Finding F12-2 (CARRIED, OPEN — owner action):** Phase 1 de-tracked the
exposed credential files (`backend/.env`, `frontend/.env.local`,
`env.production`) and sanitized docs, but the underlying secrets
(Supabase anon + service-role keys, DB password, SMTP credentials,
OpenAI key, JWT secret, crypto wallets) have **not been rotated**.
Rotation remains a blocker for any live staging work. No new secrets
were introduced anywhere in this phase; no secret values are printed in
any Phase 12 artifact.

## 2. Dependency vulnerabilities

No new dependencies were added in Phase 12. A dependency audit
(`pip-audit` / `npm audit`) was not configured in the repo; running a
full audit is deferred (noted, not performed — the phase added no
packages, so no new exposure was introduced).

## 3. Authentication & authorization

- Canonical auth: application-owned JWT (bcrypt, access+refresh,
  revocation via `refresh_tokens`), enforced by `api/deps.py`.
- Enforcement gate (Phase 11) reconciles lapsed suspension windows
  lazily on auth/gate paths; suspended users get a limited session that
  reaches only appeal surfaces.
- Supabase Auth remains only as the **legacy compatibility path** for
  the live careers frontend; it is not the source of truth for any
  canonical authorization (RBAC, Work ID, membership, governance). This
  boundary is documented in PHASE_12_SUPABASE_RECONCILIATION.md §D.
- **Verdict:** PASS (canonical surface).

## 4. Tenant isolation / IDOR-BOLA

Covered by the canonical suites: cross-tenant reads are denied even with
known UUIDs (outreach, communications, governance, enforcement,
appeals), and Phase 9/10/11 added explicit hostile-path tests. Phase 12
added no new read/write surface, so no new IDOR surface was introduced.
**Verdict:** PASS (existing enforcement + no new endpoints).

## 5. Document access

Canonical `person_documents` + `document_access_grants` + `consents`;
access is candidate-controlled and audited. Legacy storage RLS
(`auth.uid()::text = foldername[1]`) is **not** copied anywhere; the
target storage abstraction is provider-neutral with signed/controlled
access. KYC selfies are deprecated (no facial capture in canonical).
**Verdict:** PASS (design), with live storage migration gated on consent
(see reconciliation doc §I).

## 6. Admin privilege escalation

Legacy `profiles.is_super_admin` is **not** reproduced. Canonical RBAC
uses platform roles + granular permissions (`reports.*`, `enforcement.*`,
`appeals.*`, `governance.*`), least privilege, and separation of duties
(enforcement creator ≠ approver). No universal admin shortcut exists in
canonical code. **Verdict:** PASS.

## 7. SQL injection / dynamic SQL

Canonical code uses SQLAlchemy ORM + parameterized statements
(health/readiness `SELECT 1` is literal). No string-built dynamic SQL
was found in the canonical backend in this review. **Verdict:** PASS.

## 8. CORS / CSRF

CORS allowlist is env-driven (`CORS_ORIGINS`); the canonical API is a
JWT-bearer JSON API (no cookie-based CSRF surface). **Verdict:** PASS
(configuration is deployment-driven).

## 9. SSRF / path traversal / file upload

- Canonical storage is provider-neutral and **not yet wired** to any
  upload endpoint (document upload is a later phase); no new upload
  surface was introduced. Legacy storage policies remain legacy.
- No outbound-URL fetch surface in the canonical app (AI providers are
  not wired).
- **Verdict:** PASS (no new surface); upload validation rules must be
  defined when the canonical storage layer lands.

## 10. Rate limiting

Centralized policy registry (Phase 9) with consistent generic 429s that
do not leak account existence (test-enforced). Store is
development-safe in-memory; multi-instance production requires the
documented DB/Redis store swap. **Verdict:** PASS (foundation); the
production store is REQUIRES EXTERNAL INFRASTRUCTURE.

## 11. Audit integrity & logging leakage

- Every sensitive event is audited with actor/action/resource/org/
  correlation ID; Phase 9/10/11 tests assert audit rows contain **no**
  secrets, message bodies, notes, statements, or document contents.
- Request middleware logs method/path/status/duration with request IDs —
  no payloads.
- **Verdict:** PASS (test-enforced).

## 12. Infrastructure findings (this phase)

- **FIXED:** hardcoded secrets in `docker-compose.yml` (§1).
- **FIXED (config):** compose referenced missing artifacts
  (`frontend/Dockerfile`, `init.sql`, `monitoring/prometheus.yml`,
  `nginx/ssl`) that made the stack unbootable; removed with documented
  rationale.
- **OPEN (documented):** no `.github` CI/CD exists; no metrics endpoint;
  no backup/restore drills; proxy/trusted-host hardening deferred to
  deploy time. None of these weaken runtime security; they are
  operational gaps recorded in PHASE_12_PRODUCTION_INFRASTRUCTURE.md.
- **OPEN (documented):** the live Supabase project was not inspected
  (no approved credentials; known-exposed keys must rotate first) —
  schema drift in the live project is UNKNOWN.

## 13. RLS posture

No RLS was enabled anywhere. The Phase 9 artifact
(`backend/app/db/rls.py`) is the reviewed policy design; Phase 11
validated the semantics on local PostgreSQL (non-owner role sees only
its tenant rows; owner bypass confirmed as the deployment caveat). Phase
12 documents the required non-owner app role + session-marker mechanism
and a staged enablement order. **Verdict:** PASS (design + local
validation); production enablement is a guarded later step.

## 14. Overall result

**SECURITY: PASS WITH FINDINGS.** All findings are either fixed in this
phase (compose secrets/config) or documented owner/deployment actions
(credential rotation — the only true blocker; staging infrastructure;
metrics/backup completion). No new attack surface was introduced;
existing authorization, tenant-isolation, audit-hygiene, and rate-limit
tests all remain green (153 passed).