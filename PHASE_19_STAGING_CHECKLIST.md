# Phase 19 — Staging Checklist

Status key: **PASS** (evidence this phase) · **BLOCKED** (gate/operator) · **NOT APPLICABLE** · **PARTIAL**

## Gates
- [x] Git safe — HEAD `0caa411`, 63 carried entries untouched — **PASS**
- [x] Secrets safe — `backend/.env` ignored/untracked; scan clean — **PASS**
- [x] Live identity re-verified (project/DB/schema/TZ) — **PASS**
- [ ] Backup/PITR confirmed — **BLOCKED** (operator declined live writes; gate remains)
- [ ] Operator go-ahead for live reconciliation — **BLOCKED** (declined this phase)

## Database
- [x] Pre-migration baseline captured (21 tables + counts) — **PASS**
- [x] `interviews` facts re-verified (0 rows, 0 incoming FKs) — **PASS**
- [x] Reconcile script prepared + locked by tests — **PASS**
- [ ] Live rename + bootstrap + app role — **NOT APPLIED**
- [ ] Post-migration verification (101 tables, 0014, counts intact) — **NOT APPLIED**

## Local validation
- [x] SQLite suite — **250 passed / 11 skipped / 0 failed**
- [x] PostgreSQL RLS — **11/11**
- [x] Staging-mode E2E smoke — **PASS** (`P19_STAGING_SMOKE_PASS`)
- [x] Legacy backend 107 routes — **PASS**; canonical 246 — **PASS**
- [x] Frontend typecheck/lint/build — **PASS**
- [x] Careers unchanged — **PASS**

## Staging environment
- [x] Staging configuration contract proven locally (`ENVIRONMENT=staging` override, `.env` untouched) — **PASS**
- [ ] Remote staging project/DB provisioned — **BLOCKED** (operator decision; not created automatically)
- [ ] Staging frontend → staging API wiring — **PARTIAL** (config contract proven; no remote env)
- [ ] Synthetic staging data — **PARTIAL** (smoke used ephemeral tenant data, cleaned up)
- [ ] Payment mock/sandbox only — **PASS** (mock; no real-money path)
- [ ] Rate limiting store `db` in staging — **PARTIAL** (contract exists; no deployment)
- [ ] Observability (logs/health) in staging — **PARTIAL** (in-app audit + readiness endpoint proven; no aggregator)
- [ ] Staging backup/restore test — **BLOCKED** (needs staging infra + PITR)

## Launch items carried forward
- Distributed rate limiting for production (`RATE_LIMIT_STORE=db`/Redis) — **BLOCKED**
- Security headers + TLS + real CORS origins — **PARTIAL** (runbook)
- Provider provisioning (AI/voice/video/email/payment) — **BLOCKED**
- Storage policy review (3 private buckets) — **PARTIAL** (dashboard)
- Legacy key rotation — **BLOCKED** (operator)