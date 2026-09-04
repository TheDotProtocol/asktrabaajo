# PHASE 8 — Government architecture

AskTrabaajo Government is a **privacy-preserving workforce intelligence layer**. It is not a citizen database and it is not a second tenancy model.

```
PERSON
  → WORK ID
  → TALENT / OPPORTUNITY GRAPH
  → PRIVACY-PRESERVING AGGREGATION
  → GOVERNMENT WORKFORCE INTELLIGENCE
```

Government generally sees counts, distributions, skill clusters, geographic aggregates, industry aggregates, employment-record aggregates, and hiring-demand (open opportunity volume).

Government does **not** automatically see individual Work IDs, private addresses, phones, emails, government IDs, documents, KYC, salaries, messages, applications, interviews, or raw person rows.

## Organization model

Government is a first-class `Organization.kind = government` tenant. Users enter through existing membership + role + permission.

| Role | Catalog label | Permissions |
|---|---|---|
| `government_admin` | Government Admin | `orgs.read`, `workforce.aggregates.read` |
| `government_user` | Government Analyst | `workforce.aggregates.read` |

`GOVERNMENT_VIEWER` is represented by `government_user` (read-only aggregates). `GOVERNMENT_LIAISON` is **not** added — there is no authorized government↔company outreach capability yet.

No `government.*` permission codes were invented. Aggregate reads reuse canonical `workforce.aggregates.read`. Super admin still inherits all permissions through existing RBAC.

Government organizations cannot be self-served. `tenancy.create_organization` still requires a platform super admin for `government` / `platform`. The local DEV government org is inserted by bootstrap.

## Data access layer

The architectural boundary is:

```
Person / Work ID / Opportunity / Company
        ↓
app.services.government  (aggregation)
        ↓
k-threshold suppression
        ↓
/api/v1/government/* and Athena government.* tools
        ↓
Government portal
```

Government endpoints never query person tables for display. There is no `GET /government/person/{id}`.

## Privacy model

Central policy: `Settings.government_min_cohort_size` (`GOVERNMENT_MIN_COHORT_SIZE`, default **10**).

Person-cohort cells below K return `value: null` with `SUPPRESSED` (count > 0) or `INSUFFICIENT_COHORT` (count = 0). If any person bucket is suppressed, `visible_sum` is omitted so complementary subtraction cannot reconstruct the hidden cell.

If a filtered person population is below K, breakdowns are refused (`status: insufficient_cohort`).

Opportunity and employer **volume** counts are not person cohorts. Small job/company counts may be shown. Names, contacts, and private company fields are never included.

## API model

All routes live under `/api/v1/government/`.

| Route | Purpose |
|---|---|
| `GET /overview` | Executive cards + top skills |
| `GET /workforce` | Person-cohort distribution |
| `GET /workforce/geography` | Workforce by city |
| `GET /workforce/employment` | Current employment record vs none |
| `GET /skills` `/skills/demand` `/skills/gaps` | Supply / demand / gaps |
| `GET /industries` | Opportunity volume by industry |
| `GET /opportunities` | Hiring demand groupings |
| `GET /companies` | Employer organization counts |
| `GET /reports/{kind}` | Reproducible aggregate report |
| `GET /exports/{kind}` | JSON or CSV of aggregate cells |
| `GET /settings` | Membership + privacy boundaries |

Every query/export is authenticated, membership-scoped, permission-checked, filter-validated, rate-limited (`government.query` 60/60, `government.export` 10/3600), and audited with **scope only** (never cell values or person data).

## Athena model

Government Athena is no longer an empty shell. It may only invoke registered aggregate tools:

- `government.get_workforce_summary`
- `government.get_skill_summary`
- `government.get_skill_gap`
- `government.get_geographic_summary`
- `government.get_industry_summary`
- `government.get_hiring_demand`
- `government.get_opportunity_summary`
- `government.generate_report`

Each tool requires `workforce.aggregates.read`, government mode, and the same suppression layer. There are no person-search, Work ID, document, or application tools.

## Audit / export

Audit records: actor, organization, action, filter scope, timestamp. Not raw person data. Not query cell values.

Exports contain flattened aggregate rows (`section`, `key`, `value`, `status`). JSON and CSV only. PDF is **NOT IMPLEMENTED**. Person records are never exported.

## Explicitly future / not implemented

- Individual consent disclosure of a Work ID to a government org
- Government↔company outreach / messaging
- Investment / expansion request workflows (UI honesty page only)
- Precomputed warehouse / `workforce_aggregates`
- Historical time series / emerging-skills snapshots
- Geographic maps with coordinates
- Facial recognition, political or protected-characteristic profiling
