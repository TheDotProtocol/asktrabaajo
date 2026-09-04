# CURSOR WAVE 8 — Government security

## Access model

Backend is authoritative. Frontend `PortalGuard` is convenience only.

To read any Government intelligence endpoint:

1. Authenticated user
2. `workforce.aggregates.read`
3. A `government`-kind organization membership (or platform super admin)
4. If `organization_id` is supplied, the caller must be a member of **that** government org

Employer and candidate memberships never satisfy this on their own.

Government A cannot pass Government B’s `organization_id`. Cross-government private configuration is isolated by membership.

## Privacy boundary

Government APIs never return:

- person ids, Work IDs, emails, phones
- documents / KYC
- applications / interviews / messages
- individual salaries
- company names or contacts

Cells are counts or suppressed placeholders.

## Suppression

`GOVERNMENT_MIN_COHORT_SIZE` (default 10) applies to **person cohorts**.

- Below K with count > 0 → `SUPPRESSED`, `value: null`
- Empty cell → `INSUFFICIENT_COHORT`
- Any suppressed person bucket → no `visible_sum`
- Filtered person population below K → no breakdown

Filters are length-limited and centralized in `parse_filters`. Combining city + skill still cannot return a small identifiable cohort.

Opportunity / employer volume is not treated as a person cohort. That does not authorize leaking private company fields.

## Cross-tenant isolation

| Actor | Government aggregates | Other tenant private data |
|---|---|---|
| Government user | Own membership scope | No |
| Employer | 403 | Own company OS only |
| Candidate | 403 | Own Work ID only |
| Super admin | Existing RBAC (all permissions) | Existing admin governance |
| Government Athena | Registered aggregate tools only | Cannot search people |

## Athena restrictions

Government mode is granted only for `government_admin` / `government_user` roles.

Tools are explicit, schema-bound, permission-bound, and call `services.government`. There is no `government.search_person` or `government.get_work_id`. Athena cannot circumvent portal permissions.

If a cohort is below K, tools return the same suppressed envelope. The Government Athena system prompt instructs the model not to invent people or reconstruct suppressed groups.

## Audit

Actions `government.overview`, `government.workforce`, `government.geography`, `government.employment`, `government.skills`, `government.skills.demand`, `government.skills.gaps`, `government.industries`, `government.opportunities`, `government.companies`, `government.report`, `government.export` are written through `app.services.audit.record`.

Metadata is **filter scope only**.

## Exports

JSON / CSV of aggregate cells. Authorized, scoped, audited. Confirmation in the Reports UI lists data scope, period, filters, record type, and privacy status. Raw person export is impossible from these endpoints.

## Rate limits

Existing registry only:

- `government.query` — 60 / 60s
- `government.export` — 10 / 3600s

## What was not built (security-positive)

- Individual citizen search
- Unrestricted government database access
- Government-to-citizen messaging
- Autonomous decisions affecting citizens
- Protected-characteristic profiling
- Fake ministry integrations
