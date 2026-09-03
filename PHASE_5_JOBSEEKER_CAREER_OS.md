# AskTrabaajo — Phase 5 Report: Jobseeker Career OS

Phase 1: Security + Preservation · Phase 2: Architecture · Phase 3: Platform Foundation ·
Phase 4: Identity + Work ID · **Phase 5: Jobseeker Career OS** (this report)

Status: **COMPLETE — foundation layer, awaiting review.** No Phase 6 work started.
Repository state during this phase: `main`, commits `3b6e…` (see Git section).

---

## 1. Product architecture

The Jobseeker Career OS sits on the Phase 4 identity spine (PERSON → Work ID)
and adds the intelligence + workflow layer on top. Everything is one
FastAPI `/api/v1` surface, one canonical schema, one authorization model
(person-owned data; company interaction deferred to later phases).

Ownership boundaries implemented and enforced:

| Entity | Owner | Notes |
|---|---|---|
| Work DNA profile + answers | PERSON | Extensible dimensions; answer log kept |
| Career goals | PERSON | Feed matching + the Career Advisor |
| Opportunities (catalogue) | Platform / company | Person's save/dismiss/apply lives on person rows |
| Applications + events | PERSON | State machine is the only writer of status |
| Interviews | PERSON (via application) | Employer side arrives Phase 6+ |
| Offers | PERSON (via application) | Decisions explicit + audited |
| Career milestones | PERSON | Career timeline building blocks |
| Notifications | USER | In-app feed, jobseeker scope |

## 2. Jobseeker experience

Seven functional routes under `/jobseeker` on the typed API client
(`frontend/src/app/jobseeker/*`) plus the identity pages from Phase 4:

- **Home** (`/jobseeker`) — the Career Command Center: profile completion,
  Work DNA status, goal state, live counts (applications, upcoming interviews,
  pending offers), recommended opportunities with match %, advisor "next" list.
- **Work DNA** (`/jobseeker/work-dna`) — versioned 8-question assessment +
  legible dimension profile with per-dimension confidence bars.
- **Career** (`/jobseeker/career`) — advisor snapshot (summary, gaps, learning
  recommendations), career-goal CRUD, milestones.
- **Opportunities** (`/jobseeker/opportunities`) — searchable catalogue ranked
  with reasons; Apply / Save are explicit actions.
- **Applications** (`/jobseeker/applications`) — status list + per-application
  timeline; withdraw goes through the state machine.
- **Interviews** (`/jobseeker/interviews`) — upcoming list + reason-based,
  limited reschedule requests.
- **Offers** (`/jobseeker/offers`) — terms view + explicit accept/decline.

These are functional validation pages styled with the existing design tokens —
**not** the Figma product UI, which replaces the shell later.

## 3. Work DNA

- Versioned (`v1`) 8-question assessment: problem solving, work style,
  communication, risk tolerance, learning style, career motivation, leadership
  tendency, environment.
- **No single reductive score.** `compute_dimensions` maps explicit answers to
  named, human-labelled dimensions (e.g. `analytical_thinking`, `collaboration`,
  `leadership tendency`) each with a `signal` (0–1) and a `confidence` derived
  from how many answers support it.
- Raw answers are logged (`work_dna_answers`) with the profile id so any future
  adaptive engine and the audit trail can explain how a profile was derived.
- New versions/adaptive engines write through the same service — dimensions are
  an extensible JSON list, so no schema churn.

## 4. Career Advisor

Deliberately **not a chatbot** and it never invents facts. `advisor_snapshot`
reasons only over real Work ID data (roles held, strongest skills, education,
credentials, the person's stated goal, open opportunities) and returns:

- a plain-language `summary` ("Based on your Work ID, …");
- `current_position`, `roles_held`, `strongest_skills`;
- `gaps` (skills/experience/role-level, each traceable to a Work ID fact);
- a small, prioritized `learning_recommendations` list (≤3 — no catalog spam);
- concrete `next_actions`;
- an explicit disclaimer: *no career outcome is guaranteed*.

Athena will later consume the same service boundaries and add conversation on
top — never invention.

## 5. Career Path

Foundation delivered as: career goals (target role, industries, locations,
work modes, salary, relocation/remote preferences) + person-owned milestones +
advisor gap analysis. The engine can already explain *what stands between the
person and the goal*. Formal path modelling (nodes/edges with expected
duration) is a Phase 6 candidate — see Decisions.

## 6. Opportunity model

Canonical `opportunities` table normalizes the catalogue: company, title,
summary, location/country/city, remote/work mode, employment type, experience
level, seniority, industry, skills required, salary band + currency, closing
date, source + provenance (`imported_from`), status/approval flags. A person's
private stance is `opportunity_interactions` / `job_applications` — never on
the catalogue row.

**Careers compatibility:** the live Supabase careers corpus (companies, jobs,
applications, job_offers) was **not touched**. The Phase 5 migration seeds a
small provenance-marked demo corpus (`imported_from='demo_careers_corpus_v1'`,
15 opportunities mirroring AR Holdings brands/roles) so discovery and matching
work in every environment. The employer pipeline that feeds canonical
opportunities from the real corpus is a Phase 6 dependency (see §24).

## 7. Matching model

Deterministic, rule-based, fully explainable (`services/matching.py`):

```
score = Σ component_weight × component_score
weights: skills .45 · experience .20 · goal_alignment .15 · education .10 · seniority .10
```

Every result returns `components` (per-component score + human reason, with
`matched`/`missing` skill lists), `strengths`, `gaps`, `missing_skills`, and
only then `percent`. No ML claims anywhere. Skill matches are proficiency-
weighted; years of experience come from the person's real employment history.

## 8. Application lifecycle

Controlled state machine (`services/applications.py`):

- Jobseeker may: **save** (from discovered), **apply** (from saved/discovered,
  gated on ≥1 skill on the Work ID so empty profiles cannot spam companies),
  **withdraw** (from live states: applied/received/screening/on_hold).
- Every transition writes an `application_event` (from → to, note, actor) —
  the permanent application timeline.
- Raw status writes are impossible from the jobseeker API. Employer-driven
  transitions (received → screening → interview → offer) go through
  `transition_to_status` behind membership permissions in Phase 6.
- Duplicate application to one opportunity is blocked (unique constraint +
  state check). Batch apply exists server-side only for an explicit caller
  list — the hook Athena will use after explicit user authorization.

## 9. Interview workflow

Jobseeker-side interview center: upcoming/completed list, mode, duration,
interviewer, meeting link, status (`scheduled/completed/cancelled/
reschedule_requested`). Rescheduling is **policy-controlled and configurable**
(`max_reschedules_per_interview`, default 2) and requires a reason. No AI
interviewer, no facial/behavioural analysis, no deception claims — those are
later phases with separate ethical design.

## 10. Offer workflow

Offers attach to the candidate's application with terms mirrored from the
company (salary, equity, benefits, start date, location). Accept/decline is an
explicit, audited decision. **Accepting an offer moves the application to
`accepted` through the state machine** (the seed of the onboarding journey).
No binding documents are generated — the company's authoritative offer
document is referenced via `offer_document_id` only.

## 11. Career timeline

Foundation: `career_milestones` (kind, title, date, reference) — person-owned,
API-backed (list/create/delete). Milestones currently include education,
experience, employment, and credential records from the Work ID plus offers
accepted. A single unified timeline endpoint combining Work ID history +
milestones is a Phase 6 candidate (see Decisions).

## 12. Development model / 13. Learning model

The Advisor computes a small set of prioritized gaps and ≤3 learning/
certification recommendations grounded in those gaps. The catalogue of
suggestions is static and vendor-neutral (course vs certification). No
payments, no marketplace — jobseekers remain free.

## 14. Notification model

In-app notifications on the events that matter: application submitted,
interview reschedule recorded, Work DNA refreshed. `kind` is modeled
(application/interview/offer/document/career/system) so the unified
multi-channel layer (email/SMS/push/voice + preferences) attaches later
without remodelling. Unread count + read-all included on the dashboard.

## 15. API endpoints (canonical, `/api/v1/jobseeker` — 28 routes)

| Area | Endpoints |
|---|---|
| Work DNA | `GET /work-dna/questions`, `GET /work-dna`, `POST /work-dna/assessments` |
| Goals | `GET/POST /goals`, `PATCH/DELETE /goals/{id}` |
| Opportunities | `GET /opportunities` (search + explainable match), `POST /opportunities/{id}/save`, `POST /opportunities/{id}/dismiss` |
| Applications | `GET /applications`, `GET /applications/{id}` (timeline), `POST /applications` (apply), `POST /applications/batch`, `POST /applications/{id}/withdraw` |
| Interviews | `GET /interviews?upcoming=`, `POST /interviews/{id}/reschedule-request` |
| Offers | `GET /offers`, `POST /offers/{id}/decision` |
| Advisor | `GET /advisor` |
| Milestones | `GET/POST /milestones`, `DELETE /milestones/{id}` |
| Notifications | `GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all`, `GET /notifications/unread-count` |
| Dashboard | `GET /dashboard` |

Total canonical routes: **91** (was 63).

## 16. Database changes

Migration `0003_jobseeker_career_os` — **strictly additive**, 11 new tables:
`work_dna_profiles`, `work_dna_answers`, `career_goals`, `opportunities`,
`opportunity_interactions`, `job_applications`, `application_events`,
`interviews`, `offers`, `career_milestones`, `user_notifications`.

Validated locally on scratch SQLite: upgrade head (33 tables) → downgrade 0002
(all new tables dropped) → re-upgrade (seed idempotent, 15 opportunities).
**No migration was applied to any shared/production database.** No table from
the live Supabase careers schema shares a name with anything in 0003.

## 17. Authorization / 18. Privacy / 19. Security

- Every jobseeker resource is person-scoped via the caller's PERSON record;
  non-owners receive **404** (existence hidden) — covered by regression tests
  for applications, goals, milestones, interviews, offers, notifications.
- Opportunities are the only shared catalogue; save/dismiss/apply state is the
  person's own rows. Dismissed opportunities never appear in their results.
- Apply gate (≥1 skill) prevents marketplace spam; batch apply only ever runs
  on an explicit caller list.
- No secrets introduced; audit events on DNA submission, goal creation,
  application submit/withdraw, offer decisions. No sensitive payloads logged.
- `InvalidInputError` maps to the documented `422` envelope; tests assert the
  envelope shape.

## 20. Tests

Phase 5 suite (`tests_phase3/test_jobseeker_phase5.py`, 16 tests) covers:
Work DNA question set + submit + invalid-answer rejection + ownership;
opportunity listing with explainable components (`matched`/`missing`);
save → apply → duplicate-reject → timeline; empty-profile apply gate; withdraw
lifecycle + terminal-state reject; cross-user isolation on applications/goals/
milestones (404); interview center + reschedule-policy (reason required, limit
enforced); interview/offer ownership; offer decline + double-respond reject;
offer acceptance moving the application to `accepted`; dashboard aggregation;
advisor no-invention rule; notifications ownership.

**Full canonical suite: 81 passed** (was 65). Legacy backend import intact
(107 routes). Frontend: `tsc` 0 errors, eslint 0 errors, production build ✅.

## 21. Careers integration

- Existing careers platform fully preserved: no shared file changed, no
  Supabase careers table touched, existing frontend routes/seed corpus intact.
- The demo opportunity corpus is **provenance-marked and separable**; the
  mapping from the real careers `jobs` table to canonical `opportunities` is
  documented in §24 as a Phase 6 deliverable.

## 22. Known limitations

- Opportunities come from the demo corpus, not the live careers corpus (real
  ingestion needs the employer pipeline).
- Matching is deterministic heuristics — deliberately. It is not ML and makes
  no ML claims.
- Notifications are in-app only; multi-channel delivery + preferences deferred.
- No formal career-path graph, no unified timeline endpoint yet.
- Frontend pages are functional proofs, styled with existing tokens.
- SQLite remains the test dialect; Postgres-specific behavior unverified
  (parity test still the guardrail).

## 23. Production readiness (honest)

**READY:** person-owned data boundaries + isolation tests; application state
machine with audited transitions; explainable matching contract; interview
reschedule policy config; document/consent boundaries (from Phase 4).

**NOT READY:** real opportunity ingestion; employer-driven status transitions
(screening/interview/offer write-side); multi-channel notifications; RLS on
the 11 new tables; the Figma-based jobseeker UI.

**UNKNOWN:** production Postgres behaviors; real employer data volumes.

## 24. Decisions requiring approval

1. **Approve Phase 5** and the Phase 6 sequence below.
2. **Opportunity ingestion approach** (Phase 6): (a) employer job-creation
   pipeline that feeds canonical `opportunities` (recommended — careers corpus
   becomes the first native feed), or (b) a one-time compatibility import from
   Supabase `public.jobs`.
3. **Career-path modelling**: full path graph (nodes/edges, expected duration)
   in Phase 6 vs Phase 7.
4. Unified **career timeline** endpoint combining Work ID history + milestones.
5. Commit review of the pre-Phase-3 hygiene batch (still uncommitted,
   awaiting owner decision).
6. External credential rotation (outstanding from Phase 1).

## 25. Phase 6 dependencies

The next phase (Company/Recruiter ecosystem) depends on: canonical
`opportunities` as the shared catalogue (done here); the employer write-side
of the application state machine via `transition_to_status` (built here,
permission-gated there); interview scheduling create/approve/counter flows;
offer creation with authoritative offer documents; tenancy linkage
(`opportunities.company_id` → `organizations`).

---

*This phase changed no production database, deleted no Careers functionality,
introduced no payment/blockchain/Athena code, and made no AI claims. All
changes are committed on `main` in reviewable units (see Git log).*
