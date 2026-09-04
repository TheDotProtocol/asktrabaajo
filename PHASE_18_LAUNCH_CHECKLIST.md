# Phase 18 — Launch Checklist

Status key: **PASS** (verified with evidence) · **FAIL** · **BLOCKED** (operator action / gate) · **NOT APPLICABLE** · **PARTIAL**

## DATABASE
- [x] Connection via session pooler works, read-only discipline held — **PASS**
- [ ] Backup/PITR confirmed from Supabase dashboard — **BLOCKED** (operator)
- [ ] Go-ahead for the validated reconciliation bootstrap — **BLOCKED** (operator)
- [ ] Post-bootstrap verification (101 tables, revision 0014, constraints valid) — **BLOCKED**
- [ ] Live row counts recorded pre/post, no legacy count decrease — **BLOCKED**

## DATABASE RECONCILIATION
- [x] Collision inventory complete — exactly one (`interviews`), empty, no incoming FKs — **PASS**
- [x] Local simulation validates rename + `upgrade head` + app role — **PASS**
- [x] Dry-run report produced (no live execution) — **PASS**
- [ ] Live execution of rename + bootstrap — **BLOCKED** (PITR + approval)

## BACKUP/PITR
- [ ] Operator confirms scheduled backups / PITR enabled — **BLOCKED**
- [ ] RTO/RPO formally established — **NOT DEFINED**

## RLS
- [x] Legacy: 21/21 tables RLS-enabled, policies untouched — **PASS**
- [x] Canonical RLS suite 11/11 on PG — **PASS**
- [x] App role least privilege validated in sim (316 grants, zero legacy) — **PASS**
- [ ] Live canonical RLS spot-checks after bootstrap (cross-tenant probes) — **BLOCKED**
- [ ] Legacy storage/table policy re-review from dashboard — **PARTIAL** (operator)

## APP ROLE
- [x] `asktrabaajo_app` spec validated in sim — **PASS**
- [ ] Create role + grants on live (post-gate) — **BLOCKED**

## STORAGE
- [x] 3 buckets all private — **PASS**
- [ ] Per-object storage policies verified from dashboard — **BLOCKED** (operator)

## AUTH
- [x] Canonical auth routes + tests green (suite) — **PASS**
- [x] No legacy auth bypass introduced — **PASS**
- [ ] Production JWT/CORS/origin configuration — **PARTIAL** (runbook)
- [ ] Legacy anon/service key rotation — **BLOCKED** (operator)

## WORK ID
- [x] Ownership/visibility/audit tests green — **PASS**

## JOBSEEKER
- [x] Career OS routes + tests green — **PASS**
- [x] Career advisor + interview prep routes/tests green — **PASS**

## EMPLOYER
- [x] Org/company/job/pipeline routes + cross-tenant tests green — **PASS**

## AI
- [x] Athena tool/security/budget tests green; provider `none` safe — **PASS**
- [ ] Production AI provider provisioning — **BLOCKED** (operator)

## AI INTERVIEW
- [x] Session/consent/question/evaluation/report tests green — **PASS**
- [x] No facial-emotion/lie/protected-inference/autonomous-decision code — **PASS**
- [ ] Voice/video provider provisioning — **NOT CONFIGURED**

## COMMERCE
- [x] Plans/subscriptions/entitlements/usage/invoices tests green — **PASS**
- [ ] Catalog pricing decisions (operator/product) — **BLOCKED**

## PAYMENTS
- [x] Mock sandbox only; no production path — **PASS**
- [ ] Production provider selection + integration — **BLOCKED** (operator)
- [ ] Webhook endpoint re-verified behind real domain/TLS — **PARTIAL**

## EMAIL
- [ ] Provider not configured — **NOT CONFIGURED**

## VOICE / VIDEO
- [ ] Provider not configured; architecture safe-degraded — **NOT CONFIGURED**

## SECURITY
- [x] Secret scan clean; `backend/.env` ignored — **PASS**
- [x] Adversarial suites (auth/RBAC/tenant/AI/payment/interview) green — **PASS**
- [ ] Distributed rate limiting configured (`RATE_LIMIT_STORE=db`/Redis) — **PARTIAL** — multi-instance blocker
- [ ] Security headers / TLS termination verified — **PARTIAL** (runbook)
- [ ] CORS origins set for real domains — **PARTIAL** (runbook)

## OBSERVABILITY
- [x] In-app audit complete (tested) — **PASS**
- [ ] Log aggregation, metrics, dashboards — **NOT CONFIGURED**
- [ ] Retention/purge jobs scheduled — **NOT CONFIGURED** (specified)

## DISASTER RECOVERY
- [x] Rollback plans documented (rename reverse, `downgrade base`, role revoke) — **PASS**
- [ ] Backup/PITR confirmed + restore runbook — **BLOCKED** (operator)

## FRONTEND
- [x] Typecheck / lint / build green — **PASS**
- [x] `/jobseeker/ai-interview`, `/employer/ai-interviews`, `/employer/billing` in build — **PASS**
- [ ] No localhost/dev bypass in production build — **PARTIAL** (verify env wiring in runbook)

## LEGACY
- [x] Legacy backend imports at 107 routes — **PASS**
- [x] 63 carried Phase-1 entries untouched — **PASS**
- [ ] Legacy REST keys current after rotation — **BLOCKED** (operator)

## CAREERS
- [x] No canonical change to careers surfaces — **PASS**
- [x] Careers tables preserved with public-read RLS — **PASS**

## SUPPORT / FINANCE
- [x] RBAC separates support from finance; no refund via support — **PASS**
- [ ] Finance operator runbooks — **PARTIAL**
