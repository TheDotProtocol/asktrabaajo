# PHASE 7 — TALENT GRAPH & OPPORTUNITY INTELLIGENCE

Status: COMPLETE (backend + frontend + tests + docs)
Branch: `main` — commit range listed in §25
Supersedes nothing; builds on Phases 3–6 (`PHASE_6_COMPANY_EMPLOYMENT_OS.md`).

---

## 1. Mission

Phase 7 turns the canonical backend into a structured intelligence layer over
people, skills, experience, education, credentials, career paths, opportunities
and organizations. It answers **"who is relevant for this opportunity?"** and
**"what opportunities are relevant for this person?"** — deterministically,
explainably, and strictly within the Phase 4 privacy model.

**It is not** a generic search page, a LinkedIn clone, an ATS filter, or an
opaque AI ranker. No protected characteristics are ever used for ranking; no
facial/emotion/deception analysis exists anywhere; no hiring decisions are made
automatically.

## 2. Talent Graph architecture

One canonical relationship spine is **derived** from records that already exist
(Phase 4 Work ID + Phase 5/6 opportunities) rather than duplicating them:

```
PERSON ── owns ──> WORK ID sections
   │                   ├── skills  (user_skills -> canonical Skill)
   │                   ├── experiences / employments (skills_used)
   │                   └── credentials
   ▼
SKILL TAXONOMY ──< SkillAlias (normalization)      OPPORTUNITY
   │              < SkillRelationship (parents)      └─ skills_required ──> OpportunityRequirement
   └── SkillEvidence (person claim -> source record)         (raw text preserved)
```

New material is limited to what the graph genuinely needs: a taxonomy layer on
top of `skills`, evidence links, structured opportunity requirements, private
employer lists (pools/saved), advisory career-path catalogue, and governance
records. Everything else reads the existing Phase 3–6 tables.

## 3. Skill taxonomy

- The canonical row stays `app.models.work.Skill`, now extended with
  `subcategory`, `description`, `status` (additive columns, migration `0005`).
- Migration `0005` seeds a provenance-marked starter taxonomy
  (`source=asktrabaajo_taxonomy_v1` in aliases): **118 canonical skills** across
  software engineering, AI/data, design, marketing, sales, hospitality,
  healthcare, construction, finance, HR/people, leadership and education —
  deliberately mirroring the Careers corpus domains (104-job corpus feeds
  the same catalogue).
- Skills are **not** hard-coded in application code: seeds live in the
  migration, are idempotent, and future ingestion (external taxonomies) will
  insert into the same tables.
- `skills.status` supports active/deprecated so the catalogue can evolve
  without breaking `user_skills` references.

## 4. Skill normalization

`services/skills_registry.py`:

- `normalize(text)` — deterministic token: lowercase, dots removed,
  whitespace collapsed; `#` and `+` preserved so `C#`/`C++` never collapse.
  `React.js`/`ReactJS` → `reactjs`; `Node.js` → `nodejs`.
- `SkillAlias` rows hold normalized tokens and are **globally unique**, so one
  alias can never resolve to two skills. Each alias keeps `original` (raw
  value as first seen), `source`, `confidence`, `created_at`.
- `canonical_name_map(db, names)` batch-resolves raw names → canonical skill
  names (two indexed queries): exact case-insensitive name match, then
  normalized alias. **Unresolvable values map to themselves** — the original is
  never silently destroyed.
- The Work ID add-skill path (`PUT /api/v1/work-id/skills`) now routes through
  `ensure_skill`: free text that matches an alias converges on the canonical
  skill instead of creating a duplicate taxonomy row; genuinely new skills are
  created with their own alias. (This is the one behavior change to an
  existing endpoint; Phase 3–6 suites pass unchanged.)

## 5. Skill evidence

`SkillEvidence` links a person's skill claim to the Work ID record it came
from (`reference_type`/`reference_id` — user_skill, work_experience,
employment, credential):

- `refresh_person_evidence` derives evidence from the person's OWN records
  (delete + rebuild, so the graph always mirrors current Work ID data).
- Evidence `verification_status` mirrors the source record. A self-declared
  skill is **never** marked verified; only records carrying
  `verified`/employer-verified status propagate verified evidence.
- Privacy: an employer sees evidence only from PUBLIC source sections
  (`_evidence_snapshot` with `own_view=False`); the person's own view sees
  everything.

## 6. Experience intelligence

- Experience is not copied: matching and discovery read the canonical
  `work_experiences`/`employments` tables.
- Discovery aggregates **years experience** (max span across experiences),
  **latest role** (title/company/current) and **roles held** — the same values
  the Phase 5 matcher already computes, exposed through the graph for
  employer discovery.
- Experience `skills_used` feeds `SkillEvidence` so a skill shown to an
  employer can state its origin.

## 7. Career paths

- `career_paths` + `career_path_steps` catalogue tables are seeded with five
  advisory paths (Frontend Engineering, Hospitality Operations, Nursing & Care,
  Construction Delivery, Data & Analytics) — each step carries role title,
  seniority and the canonical skills the rung commonly needs.
- Career paths are explicitly advisory. Nothing here claims a path is
  deterministic or guarantees progression; the UI and the API both say so.

## 8. Opportunity intelligence

- One opportunity universe stays authoritative (Phase 5 `Opportunity`, fed by
  Phase 6 `JobPosting.publish` and the Careers ingestion adapter).
- `OpportunityRequirement` adds structured requirements per opportunity with
  **raw employer wording preserved** (`raw_text`), `requirement_kind`,
  `min_years` (regex from prose like "3+ years") and a canonical `skill_id`
  link **when exactly one token resolves** — ambiguous prose stays unlinked so
  requirements are never invented.

## 9. Requirement normalization

`normalize_opportunity_requirements(db, opp)` is idempotent per
(opportunity_id, raw_text), resolves the whole string first, then falls back to
single-word resolution only when exactly one distinct skill resolves
("3+ years React experience" → React; "React and TypeScript" stays unlinked).

## 10. Matching architecture

ONE matching engine (`services/matching.py`) serves both sides:

- **Candidate → opportunities** (jobseeker): unchanged weighted components
  (skills .45, experience .20, goal .15, education .10, seniority .10) with
  per-component reasons.
- **Opportunity → candidates** (employer): the same component functions with
  goal_alignment excluded — **employers never read a candidate's private
  career goals**. Only the goal owner's own jobseeker flow uses goals.
- Taxonomy awareness was added to the engine: candidate skill names and
  opportunity requirement names are canonicalized through `skill_aliases`, so a
  candidate who typed `ReactJS` matches an opportunity requiring `React`.

## 11. Match explanations

Every ranked result ships with: percent + per-component reasons, matched /
missing skills, strengths and gaps (human text), a qualitative **mode**
(`strong` / `potential` / `career_transition` / `explore`), and `coverage`.
The mode rules are deterministic:

| Mode | Rule |
| --- | --- |
| strong | score ≥ 0.7 and coverage ≥ 0.66 |
| potential | score ≥ 0.55 or coverage ≥ 0.5 |
| career_transition | coverage ≥ 0.3 and years ≥ 70% of required minimum |
| explore | otherwise |

Percentages are never shown bare — the UI always pairs them with reasons.

## 12. Candidate discovery

`/api/v1/talent/{org}/candidates/search` with q / skills / location / country /
min_years filters, paginated (`page`, `page_size`, max 100). Sorting is
relevance (name/headline text hits weighted above skill hits), then experience.

Discovery eligibility = **profile section PUBLIC** (opt-in; default everywhere
is private). Skills/location filters are applied only against public sections —
a person whose relevant section is private is excluded from that filtered
search rather than probed.

## 13. Candidate privacy

- Only PUBLIC professional data is returned: name/headline from `profile`,
  skills from `skills`, experience from `experience`, location only from
  `contact`. Phone numbers, documents, credentials and private sections never
  appear — verified in tests (`"phone" not in str(profile)`).
- Ranked matching additionally requires profile+skills+experience+education
  public (a fully discoverable professional summary).
- Pipeline-context candidates (people who applied to the org) follow the
  Phase 6 `candidate_summary` disclosure.
- Each result card carries a `disclosure` object telling the UI exactly which
  sections were visible.

## 14. Opportunity discovery

Jobseeker side gains real intelligence on the same engine:

- `GET /api/v1/jobseeker/opportunities/{id}` — match + requirements +
  skill-gap analysis with personal evidence.
- `GET /api/v1/jobseeker/career/intelligence` — roles within reach
  (≥70% match), roles to grow into (45–69%), aggregated skill gaps across
  nearly-matched roles, and advisory next-step advice when the person's goal or
  current title sits on a seeded path.

## 15. Skill gap analysis

`_gap_analysis` (and its jobseeker wrapper `own_skill_gap_analysis`) returns:

```
matched: [{skill, evidence: [{evidence_type, verification_status}]}]
gaps:    [{skill, source: opportunity_requirement}]
coverage
```

Gaps come only from the opportunity's actual requirements. Matched skills carry
evidence links so "why do we think they know React" is answerable.

## 16. Career intelligence foundation

`services/talent.py::career_intelligence(person_id)` — computed over the
caller's own Work ID and the live active catalogue (≤200 opportunities per
call, documented ceiling). Includes a capability map (years, roles, skills with
level/years/evidence counts, verified-skill count), current position, goal,
within-reach/grow lists, data-grounded development suggestions (missing skills
counted across 55–79% matches), and path advice. Ends with a disclaimer; no
guarantees, no fabricated facts.

## 17. Talent pools

- `talent_pools` (organization-scoped, unique name per org) +
  `talent_pool_members`. Pool names/members/notes are private to the owning
  organization.
- Add-member is gated on `person_visible_to_org` (discoverable OR an
  application exists in the org) — a private person with no relationship is
  rejected with 404.
- RBAC: `pools.manage` (new catalog permission) is granted to org_admin, hr
  and recruiter. Pool list/detail/members CRUD all re-check membership.

## 18. Search architecture

- Structured, deterministic Postgres/SQLite filtering (no vector DB yet, per
  the brief). Pagination everywhere; no endpoint loads the whole graph.
- The search interface is intentionally narrow so a semantic layer could be
  added later behind the same service boundary — documented as future work, not
  built speculatively.
- `candidate_search_events` records who searched, in which org, with which
  filters and result counts (filters only — never candidate rows).

## 19. Data provenance

- Skills: alias rows carry `source` (`taxonomy_seed`/`manual`) and confidence.
- Evidence: `SkillEvidence.source` + reference ids; verification mirrors the
  source record.
- Opportunities: unchanged provenance (`source`, `imported_from`); the Careers
  adapter (Phase 6) remains the only careers-compat ingestion path.
- Requirements: `raw_text` preserves employer wording; `skill_id` links only
  when a resolution is unambiguous.

## 20. Freshness

- Evidence is derived fresh from Work ID records on read (`refresh_person_evidence`
  inside evidence snapshotting) — old records never masquerade as current.
- Match explanations and intelligence are computed live from current rows.
- `Skill.status=deprecated` and requirement re-linking on re-normalization give
  the taxonomy a path to age out stale entries.
- No "verified recently / last updated" badges yet: verification dates already
  exist on credentials (`verified_at`) and are surfaced in Work ID; surfacing
  them in discovery is listed as a Phase 8 refinement.

## 21. AI boundary

The deterministic platform owns identity, permissions, skills, evidence,
verification, applications, jobs and companies. The graph exposes **tool-safe
service functions** (`search_candidates`, `match_candidates_for_opportunity`,
`candidate_profile_for_org`, `own_skill_gap_analysis`, `career_intelligence`,
pools/saved CRUD) that enforce authorization internally. An LLM can be pointed
at these later; it can never bypass the permission checks because there is no
data path that skips them.

## 22. Athena preparation

No Athena is implemented. The service functions above are exactly the
permissioned tools Athena would call ("show strongest candidates for this
job", "why does this candidate match", "which candidates are waiting",
"find me candidates with X skills") — each validates membership + permission +
tenant on every call.

## 23. Government boundary

Nothing in Phase 7 exposes individual records to government. `government_*`
roles hold only `workforce.aggregates.read` (catalog, Phase 3) which no Phase 7
route implements. Aggregate dimensions (country, city, industry, skill,
seniority) already exist on public rows and can feed a future aggregate portal
without any individual-level endpoint.

## 24. Database changes

Migration `0005_talent_graph` — STRICTLY ADDITIVE, validated
upgrade → downgrade (38 tables) → re-upgrade (48 tables) on scratch SQLite:

- `skills` += nullable `subcategory`, `description`, `status`
- New tables: `skill_aliases`, `skill_relationships`, `skill_evidence`,
  `opportunity_requirements`, `career_paths`, `career_path_steps`,
  `talent_pools`, `talent_pool_members`, `saved_candidates`,
  `candidate_search_events`
- Seeds: 118 canonical skills, 124 aliases, 40 relationships, 5 career paths
  (18 steps) — all idempotent by key
- RBAC: permissions `candidates.search`, `pools.manage` + role mappings
  (org_admin/hr/recruiter); downgrade removes exactly what it added

**Migrations applied: none** to any shared/production database. All validation
ran on isolated scratch SQLite; the conftest production-refusal guard is
unchanged.

## 25. API changes

New org-scoped `/api/v1/talent` router (17 routes, membership +
`candidates.search`/`pools.manage` on every route):

- `GET/POST .../skills`, `GET .../skills/categories`, `GET .../skills/{id}`
- `POST .../skills/normalize`
- `GET .../candidates/search`, `GET .../candidates/saved`,
  `GET .../candidates/{person_id}[?opportunity_id=]`,
  `POST/DELETE .../candidates/{person_id}/saved`
- `GET/POST .../pools`, `GET/DELETE .../pools/{pool_id}`,
  `POST .../pools/{pool_id}/members`,
  `DELETE .../pools/{pool_id}/members/{person_id}`
- `GET .../opportunities/{opportunity_id}/candidates`
- `GET .../opportunities/{opportunity_id}/requirements`

Jobseeker-side additions (same backend, no second API):

- `GET /api/v1/jobseeker/opportunities/{opportunity_id}` (detail + match +
  gap + requirements)
- `GET /api/v1/jobseeker/career/intelligence`

Canonical surface grew 119 → **138 routes**. Audit events added for
`talent.search`, `talent.candidate.viewed/saved/unsaved`,
`talent.pool.created/deleted/member_added/member_removed`,
`talent.opportunity.matches.viewed`.

## 26. Frontend changes

- `/company/candidates` — discovery workspace with tabs: Search, Saved,
  Pools, Ranked matches (per published job). Every card shows disclosure and
  reasons.
- `/company/candidates/[id]` — progressive-disclosure profile with a live
  "why this person matches" comparison against any of the company's published
  jobs.
- `/jobseeker/opportunities/[id]` — opportunity intelligence (match, gaps with
  evidence, structured requirements, apply/save).
- `/jobseeker/career` — new Career Intelligence panel (within reach / grow
  into / skill development / advisory next step).
- Opportunity cards now link to their detail pages.
- Nav: Company shell gains "Candidates".
- All data flows through the typed API client; new TS contract types in
  `src/lib/api/types.ts`.

## 27. Security

- Discovery opt-in is privacy-by-default: nothing is discoverable until the
  person sets their profile section to PUBLIC.
- Filters never probe hidden sections; ranked matching requires a fully public
  professional summary; employers never read private career goals.
- Membership + role-permission + tenant scoping on every talent route (403 for
  non-members before row lookups; 404 hides other tenants' rows).
- Save/pool operations validate the candidate is legitimately visible to the
  org (discovery or pipeline).
- No protected characteristics, no facial/emotion/deception analysis, no
  personality claims from photographs.
- Search events store filters only; audit records carry no sensitive payloads.

## 28. Tenant isolation

Tested: Company A cannot list/detail Company B pools (403), cannot reach B's
opportunity candidate matches (403), and sees an empty pool list in its own
org. B cannot save a private non-applicant person (404). Recruiters without
`candidates.search` (hiring_manager) get 403 on search and pools.

## 29. Tests

`backend/tests_phase3/test_talent_phase7.py` — 14 new tests, **108 total pass**
(94 prior + 14). Coverage:

- normalization converges `React.js`/`ReactJS` → one canonical skill; raw
  values preserved when unresolvable
- evidence derives from Work ID records; self claims never verified
- private person never appears in discovery; private skills excluded from
  skill-filtered search (never probed)
- alias search finds canonical candidates; search pagination + governance
  events
- ranked matches explainable; applicants excluded; partially-private
  candidates not ranked; cross-tenant ranked matches hidden
- candidate profile progressive disclosure + save/unsave
- talent pools org-isolated, visibility-gated, member add/remove
- hiring_manager cannot search or manage pools (RBAC)
- requirement normalization preserves raw prose, parses min years, links
  canonical skills
- jobseeker gap analysis + career intelligence; cross-user ownership is
  structural (no route reads another person's data)

## 30. Performance

- Pagination on every list; candidate scans for ranked matching run over
  discoverable people only and are capped per page (scan of the full eligible
  set is in-memory for the current scale — documented ceiling; a Postgres-side
  materialized index is the recommended optimization when the graph grows).
- `canonical_name_map` batches alias lookups (2 queries per unique name set).
- Evidence snapshot refreshes once per response, not per skill.
- No vector/semantic search was introduced; the search boundary is ready for
  it.

## 31. Known limitations

- Passive discovery requires per-section PUBLIC visibility; a single
  "open to opportunities" toggle that flips the professional scopes at once is
  a UX follow-up (privacy model already supports it).
- Matching scans in memory over the eligible set; at large scale this moves to
  indexed/materialized queries (Postgres GIN or a future search service).
- `career_intelligence` caps the opportunity scan at 200 rows per call.
- Path advice matches only seeded role titles; full role-title normalization
  for arbitrary titles is future work.
- Prose requirement linking is single-skill only; compound requirements
  ("React and TypeScript") stay unlinked (raw text still preserved).
- Evidence verification badges in the discovery UI (visible `verified` dates)
  are Phase 8 UI work — the data exists.
- Existing Careers platform, corpus, frontend and Supabase tables: untouched.

## 32. Production readiness

READY: additive migration validated roundtrip; all 108 canonical tests +
legacy import (107 routes) green; frontend typecheck/lint/production build
green; tenant isolation and privacy proven by tests; no production/shared DB
was touched.

NOT READY / NEXT: RLS on Postgres still to be designed against the canonical
schema (config/RLS phase); live seed of the taxonomy on a shared database is
pending approval; real-volume search performance needs the indexed
materialization above; email verification and notification delivery channels
remain unconfigured (as in earlier phases).

UNKNOWN: Postgres planner behavior for the batch alias queries at scale;
careers-corpus ingestion into a shared environment.

## 33. Phase 8 dependencies

Phase 8 (per the migration strategy) should depend on:

1. Approval of this report + Phase 7 on `main`.
2. A decision on live taxonomy/seed application to a shared Postgres
   (migration `0005` is ready; the same SQL file can run against Supabase after
   review).
3. The "candidate contact / controlled outreach" design — discovery currently
   stops at the profile (by design); messaging needs the Phase 2 controlled
   communication layer before any direct contact is exposed.
4. The RLS/config hardening phase before production traffic.

## 34. Decisions requiring approval

- (a) Approve Phase 7 and its 6 commit set; continue to Phase 8.
- (b) Whether to apply migration `0005` + taxonomy seed to a shared Postgres
  now (recommended: on staging first, SQL reviewed, rollback = downgrade
  `0005`).
- (c) Whether candidate outreach (contact) becomes the Phase 8 headliner
  (recommended) or the Jobseeker-side "availability/one-tap discoverable"
  toggle.
- (d) Carried items from earlier phases remain open: the Phase 1 hygiene batch
  (23 modified + 40+ untracked files, deliberately untouched) and external
  credential rotation.

---

### Git state (Phase 7)

6 logical commits on `main`, nothing pushed, history untouched,
`backup/pre-phase-1` intact. Files:

**Modified (11):** `backend/app/api/v1/{jobseeker,router,workid}.py`,
`backend/app/models/{__init__,catalog,enums,work}.py`,
`backend/app/services/matching.py`,
`frontend/src/app/company/layout.tsx`,
`frontend/src/app/jobseeker/{career,opportunities}/page.tsx`,
`frontend/src/lib/api/types.ts`

**Created (10 + this report):**
`backend/alembic/versions/0005_talent_graph.py`,
`backend/app/{api/v1/talent.py,models/talent.py,schemas/talent.py,
services/{skills_registry,talent}.py}`,
`backend/tests_phase3/test_talent_phase7.py`,
`frontend/src/app/company/candidates/{page.tsx,[id]/page.tsx}`,
`frontend/src/app/jobseeker/opportunities/[id]/page.tsx`
