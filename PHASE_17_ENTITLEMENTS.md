# PHASE 17 — ENTITLEMENTS

## 1. Resolution chain

Every paid capability resolves centrally through:

```
User → Organization → Subscription → Plan → Entitlement
```

The single entry point is `commerce.entitlements_for(db, org_id)`,
which returns every controlled feature code with its limit, current
usage, remaining allowance, and a within-limit flag. No route embeds a
billing check; paid features (added in later phases) call this one
service.

## 2. Controlled feature codes

Defined in `app/models/enums.py` (`ENTITLEMENT_CODES`):

| Code | Meaning |
| --- | --- |
| `jobs.create` | Job postings created |
| `jobs.active` | Concurrent active (published) postings |
| `candidate.search` | Candidate discovery searches |
| `candidate.outreach` | Outreach requests to candidates |
| `ai.athena` | Athena assistant usage |
| `ai.interview` | AI interview sessions |
| `analytics` | Analytics access |
| `premium_support` | Premium support entitlement |

Only these codes can appear in `commerce_plan_entitlements` or in
`record_usage` — unknown codes are rejected, so limits cannot be
bypassed by inventing feature strings.

## 3. FREE plan seed (the only catalog plan)

The FREE plan (`commerce_plans.code='free'`, price `0.00`) is seeded by
migration 0014 with these entitlements:

- `jobs.create`: 5, `jobs.active`: 5
- `candidate.search`: 20, `candidate.outreach`: 5
- `ai.athena`: 20, `ai.interview`: 0
- `analytics`: unlimited, `premium_support`: 0

Jobseeker-core functionality (Work ID, discovery, applications, career
intelligence) is NOT represented by any entitlement code — it is
unconditionally free by architecture, never gated.

## 4. Usage accounting

Two sources feed `usage_summary`:

1. **Platform-table counts** for features that map to real tables
   (`job_postings`, `job_postings` active where status published,
   `candidate_search_events`, `outreach_requests`, `ai_usage_log`,
   `ai_interview_sessions`) — counted with `COUNT(*)` scoped to the
   organization.
2. **Explicit usage records** (`usage_records`) written through
   `commerce.record_usage` — validated (code must be in
   `ENTITLEMENT_CODES`, quantity never negative), tenant-scoped, and
   audited.

All counts are per-organization. Cross-tenant usage leakage is tested
(org A's `analytics` usage of 3 never appears in org B's summary).

## 5. Safe default

An organization with no subscription resolves entitlements from the
FREE plan (`_free_plan_id`), so the platform never encounters an
"unentitled" dead end and jobseeker functions are never blocked by
missing billing state.

## 6. Where limits are enforced

Phase 17 does NOT yet switch any employer feature onto an entitlement
gate — that is a product decision for a later phase (and would be
applied at the service boundary, never in route code). The entitlement
service, plan catalog, usage accounting, and tests are the verified
foundation for that switch.
