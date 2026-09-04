# CURSOR WAVE 8 CLOSURE — Government OS + workforce intelligence

**Wave 9:** not started  
**Hosted database:** **UNTOUCHED**  
**Canonical application GitHub push:** **NO**  
**Deploy:** **NO**

AskTrabaajo Government is a privacy-preserving intelligence layer over the workforce ecosystem. It is not “government gets the database.”

```
PEOPLE → WORK ID → TALENT GRAPH → PRIVACY-PRESERVING AGGREGATION → GOVERNMENT OS
```

## Scorecard

| Check | Result |
|---|---|
| GOVERNMENT LOGIN | **PASS** (`akumartrabaajo@gmail.com`, existing password) |
| COMMAND CENTER | **PASS** |
| WORKFORCE / SKILLS / GEO / INDUSTRY / OPPORTUNITIES / COMPANIES | **PASS** |
| REPORTS + JSON EXPORT | **PASS** |
| GOVERNMENT ATHENA | **PASS** (registered aggregate tools only) |
| K-THRESHOLD | **PASS** (Python visible; RareSkillDEV suppressed; Sparse Town refused) |
| NO PERSON LOOKUP | **PASS** (no `/government/person/{id}`) |
| CROSS-TENANT | **PASS** (employer 403; Government B org id 403) |
| CANDIDATE / EMPLOYER REGRESSION | **PASS** (suite + Playwright jobseeker/company) |
| FRONTEND TSC / LINT / BUILD | **PASS** / **PASS_WITH_WARNINGS** / **PASS** |
| BACKEND tests_phase3 | **PASS** (11 skipped without `TEST_PG_URL`) |
| POSTGRES RLS `p14_test` | **PASS** 11/11 |
| ALEMBIC | **NOT REQUIRED** — no new revision |
| SUPABASE PUSH | **NO** |
| BROWSER QA | **YES** (Playwright desktop 1440×900 + mobile 390×844) |
| PIXEL-PERFECT FIGMA | **NOT CLAIMED** |
| WAVE 9 | **NOT STARTED** |

## 1. Executive summary

Wave 8 adds a Government Command Center that answers aggregate questions — where the workforce is, which skills appear, where opportunities exist — without exposing people. Aggregation and k-threshold suppression live in `app.services.government`. The portal reuses the existing OS shell. Government Athena can only call eight registered aggregate tools.

## 2. Government architecture

See `PHASE_8_GOVERNMENT_ARCHITECTURE.md`. One tenancy model (`Organization.kind = government`). Permission `workforce.aggregates.read`. Roles `government_admin` / `government_user`.

## 3. Database changes

**NONE.** Live SQL over existing person, skill, job, and company tables. See `PHASE_8_GOVERNMENT_DATA_MODEL.md`.

## 4. API changes

`/api/v1/government/{overview,workforce,workforce/geography,workforce/employment,skills,skills/demand,skills/gaps,industries,opportunities,companies,reports/{kind},exports/{kind},settings}`.

## 5. RBAC changes

No new permission codes. No new roles. Existing government catalog is used.

## 6. Privacy model

`GOVERNMENT_MIN_COHORT_SIZE` default 10. Person cells below K are `SUPPRESSED` / `INSUFFICIENT_COHORT` with `value: null`. Complementary totals omitted when any person cell is suppressed. Filtered person population below K refuses breakdowns.

## 7. Aggregation model

PostgreSQL/SQLite `COUNT` / `GROUP BY`. Skill demand = published jobs listing the skill. Gap = demand − unsuppressed supply, else `INSUFFICIENT DATA`. Opportunity/employer volume is not a person cohort.

## 8. Government UI

Routes under `/government/*` with persistent privacy banner. Investment is an honesty **FUTURE** page.

## 9. Figma mapping

File `IGQTJOpvt7odmdHjLazDDA`. See `CURSOR_WAVE_8_GOVERNMENT_UI.md`. Implemented intelligence screens; tenders/messages/programs/tasks not built.

## 10. Athena Government

Eight aggregate tools. No person/Work ID/document tools. Mode granted to government roles only.

## 11. Reports

`workforce`, `skills`, `regional`, `industry`, `hiring_demand`, `skill_gap`. Queryable aggregates. No person snapshots stored.

## 12. Exports

JSON and CSV of aggregate cells. PDF **NOT IMPLEMENTED**. Confirmation lists scope, period, filters, record type, privacy status. Audited.

## 13. Audit

`audit.record` with actor, org, action, filter scope. No cell values. No person data.

## 14–16. Security / isolation / K tests

`backend/tests_phase3/test_government_wave8.py` — membership 403, no person route, k-threshold, complementary-sum hide, volume buckets, Government B isolation, employer 403, settings, report, export, Athena tool list, invalid filter/format.

## 17. Browser QA

`scripts/wave8_government_qa.mjs` → `wave8-qa/localhost/`. Desktop: command center, workforce, skills, geography, industries, opportunities, companies, reports, Athena, investment (future), settings, jobseeker + employer regression. Mobile: command center, skills, settings.

Verified in-browser: registered workforce 18, Python 12, RareSkillDEV SUPPRESSED, K=10, AskTrabaajo DEV Government membership, privacy banner.

## 18. Frontend tests

`npx tsc --noEmit` PASS. `npx eslint src` 0 errors, 5 pre-existing Careers hook warnings. `NEXT_DIST_DIR=.next-wave8 npm run build` PASS (government routes present).

## 19. Backend tests

`pytest tests_phase3` PASS. Athena registry count updated 39 → 47.

## 20. PostgreSQL tests

Local `p14_test` RLS: 11/11 PASS. No new government schema to migrate.

## 21. SQLite tests

Phase 3 harness (in-memory) PASS. Isolated `asktrabaajo_wave6.db` used for localhost QA.

## 22. Migration status

No Alembic revision. Upgrade/downgrade **NOT REQUIRED**.

## 23. Supabase status

Hosted `zrvrjqwboylvvzusorry` **UNTOUCHED**. No `supabase db push`. No reset.

## 24. DEV account status

`akumartrabaajo@gmail.com` unchanged password (gitignored `backend/.wave7-dev-account`). Not super_admin. Memberships: implicit jobseeker + `org_admin` of AskTrabaajo DEV Company + `government_user` of AskTrabaajo DEV Government.

## 25. DEV Government organization

**AskTrabaajo DEV Government** (`asktrabaajo-dev-government`). Not a real ministry.

## 26. Git commits

Local only. Prefix `wave8:`. Not pushed.

## 27. HEAD

Recorded in `PROJECT_STATUS.json` after the Wave 8 documentation commit.

## 28. Working tree

Wave 8 files committed. Unrelated Careers/legacy dirt remains unstaged and is **not** part of Wave 8.

## 29. Known limitations

- No coordinate map (city labels only)
- No historical time series / emerging skills
- Employment labels are Work ID current-record observations, not official labour statistics
- Company views are counts only (no names)
- Government audit UI not built (server audit exists)
- PDF export not built
- Isolated `next build` may reformat `tsconfig.json` if run without restoring it

## 30. Future capabilities

- Person-consented scoped Work ID disclosure
- Government↔industry outreach
- Investment / expansion request workflows
- Warehouse / `workforce_aggregates`
- Tenders, programs, alerts, tasks (Figma-only)

## Capability classification

| Capability | Status |
|---|---|
| Government login + Command Center | IMPLEMENTED · FUNCTIONALLY VERIFIED · VISUALLY VERIFIED |
| Workforce / skills / geography / industry / opportunities / companies | IMPLEMENTED · FUNCTIONALLY VERIFIED · VISUALLY VERIFIED |
| Reports + JSON/CSV export | IMPLEMENTED · FUNCTIONALLY VERIFIED |
| Government Athena aggregate tools | IMPLEMENTED · FUNCTIONALLY VERIFIED · VISUALLY VERIFIED (workspace opened) |
| K-threshold + complementary-sum protection | IMPLEMENTED · FUNCTIONALLY VERIFIED · VISUALLY VERIFIED |
| Cross-tenant isolation | IMPLEMENTED · FUNCTIONALLY VERIFIED |
| Investment / outreach / consent disclosure | FUTURE / NOT IMPLEMENTED |
| Citizen search / Work ID browse | NOT IMPLEMENTED (refused) |
| Maps / time series / PDF / ministry integrations | BACKEND-LIMITED or NOT IMPLEMENTED |
| Pixel-perfect Figma | NOT CLAIMED |
| Production deploy / hosted schema | NOT TESTED (intentionally untouched) |

**STOP AFTER WAVE 8.**
