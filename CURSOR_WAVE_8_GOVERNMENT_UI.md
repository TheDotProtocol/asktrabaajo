# CURSOR WAVE 8 — Government UI

Design source: [AskTrabaajo — Government Portal](https://www.figma.com/design/IGQTJOpvt7odmdHjLazDDA/AskTrabaajo---Government-Portal) (`IGQTJOpvt7odmdHjLazDDA`).

Canonical canvas: **1440 × 1024**. Implementation reuses the Candidate/Employer OS (black / gold / 240px nav), with a persistent privacy banner.

This is **not** a pixel-perfect clone of every Figma frame. Decorative national statistics, LIVE telemetry search, and ministry chrome are not copied as live data.

## Routes

| Route | Screen | API | Status |
|---|---|---|---|
| `/government` | Command Center | `GET /government/overview` | IMPLEMENTED |
| `/government/workforce` | Workforce distribution | `GET /government/workforce` | IMPLEMENTED |
| `/government/geography` | Workforce by city | `GET /government/workforce/geography` | IMPLEMENTED |
| `/government/skills` | Supply / demand / gaps | `GET /government/skills` | IMPLEMENTED |
| `/government/industries` | Hiring demand by industry | `GET /government/industries` | IMPLEMENTED |
| `/government/opportunities` | Opportunity volume | `GET /government/opportunities` | IMPLEMENTED |
| `/government/companies` | Employer landscape | `GET /government/companies` | IMPLEMENTED |
| `/government/reports` | Reports + JSON export | `GET /government/reports/{kind}`, `/exports/{kind}` | IMPLEMENTED |
| `/government/athena` | Government Athena | Athena session `mode=government` | IMPLEMENTED |
| `/government/settings` | Access + privacy boundaries | `GET /government/settings` | IMPLEMENTED |
| `/government/investment` | Expansion intelligence | — | FUTURE (honesty page) |

Employment and education are **group-by options** on Workforce, not separate fake labour-statistic products.

## Components

- `GovernmentShell` — 240px OS nav, mobile drawer, privacy banner
- `IntelligenceUI` — `MetricCard`, `BucketList`, `FilterBar`, `PrivacyNote`
- `frontend/src/lib/api/government.ts` — typed client
- Existing `PortalGuard allow="government"`, `AthenaWorkspace portal="government"`

## Figma frame mapping

| Figma frame | Node | Route | Classification |
|---|---|---|---|
| `gov-command-center` | `5:8` | `/government` | IMPLEMENTED (aggregate cards; no fake LIVE national KPIs) |
| `gov-workforce-map` | `5:244` | `/government/geography` | BACKEND-LIMITED (city buckets; no coordinate map) |
| `gov-skills-intelligence` | `5:599` | `/government/skills` | IMPLEMENTED |
| `gov-employment-intelligence` | `5:865` | `/government/workforce?group_by=employment` | IMPLEMENTED (observational employment records) |
| `gov-education-intelligence` | `5:1101` | `/government/workforce?group_by=education` | IMPLEMENTED |
| `gov-industry-intelligence` | `7:1321` | `/government/industries` | IMPLEMENTED |
| `gov-investment-opportunities` | `7:1680` | `/government/investment` | FUTURE |
| `gov-job-creation` | `7:1895` | `/government/opportunities` | BACKEND-LIMITED (opportunity volume, not “jobs created”) |
| `gov-company-expansion` | `7:2293` | `/government/companies` | BACKEND-LIMITED (counts only; no named expansion pipeline) |
| `gov-communication` | `7:2552` | — | NOT APPLICABLE / FUTURE (no government messaging) |
| `gov-tenders` | `7:2745` | — | NOT APPLICABLE |
| `gov-athena-assistant` | `7:2987` | `/government/athena` | IMPLEMENTED (registered aggregate tools only) |
| `gov-workforce-programs` | `7:3186` | — | FUTURE |
| `gov-policy-intelligence` | `7:3461` | — | FUTURE |
| `gov-reports` | `7:3622` | `/government/reports` | IMPLEMENTED |
| `gov-alerts` | `7:3826` | — | FUTURE |
| `gov-tasks` | `7:4027` | — | NOT APPLICABLE |
| `gov-executive-dashboard` | `7:4247` | `/government` | IMPLEMENTED (same Command Center; no fabricated exec stats) |
| `gov-data-governance` | `7:4425` | `/government/settings` | BACKEND-LIMITED (privacy policy display) |
| `gov-access-control` | `7:4632` | `/government/settings` | BACKEND-LIMITED (membership list) |
| `gov-audit-trail` | `7:4796` | — | BACKEND-LIMITED (server audit exists; no government audit UI) |
| `gov-global-workforce` | `7:4993` | `/government/geography` | BACKEND-LIMITED (city labels only) |
| `gov-ecosystem` | `7:5169` | — | NOT APPLICABLE |

Figma nav items **Tenders**, **Programs**, **Tasks**, **Messages** are **NOT APPLICABLE** or **FUTURE**. They were not built as live routes.

## Visual status

- Language: national workforce intelligence, not HR operations.
- Persistent indicator: “Privacy-protected aggregate data · Individual records are not exposed”.
- Empty / suppressed / insufficient states render labels, not empty charts pretending to have data.
- Pixel-perfect vs Figma: **NOT CLAIMED**.
