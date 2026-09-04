# Phase 15 — Career Advisor

The Career Advisor is a deterministic intelligence layer over the candidate's
**own** Work ID. It is not a generic chatbot: every structured claim it can
make is computed by canonical application code from canonical platform data.
Athena (when used conversationally) explains those deterministic results — it
never reconstructs the candidate's history from raw records and never invents
requirements.

## Design principles

1. **Structured truth first.** Digests, gaps, paths, recommendations and plans
   are produced by `app/services/career_advisor.py`. The LLM, when present,
   phrases the explanation; the facts come from the service.
2. **Minimum necessary data.** The digest is a whitelist. Government IDs,
   passport/tax numbers, KYC state, document contents, contact details,
   passwords and unrelated private messages never enter the digest or the
   Athena context (deny-list enforced by tests).
3. **Verified vs unverified is explicit.** Every credential is labelled with
   its canonical state (`verified` / `unverified` / `pending` / `expired` /
   `revoked`). An unverified credential is never described as verified.
4. **Explainability.** Each recommendation carries structured reason factors.
5. **No guarantees.** Career advice never promises employment outcomes.

## Capabilities

### Profile digest (`GET /api/v1/career-advisor/digest`, `career.get_profile_digest`)

Whitelisted professional summary built from the caller's person profile:

- current position and experience summary (roles, dates, employers)
- education summary
- credentials with verification state
- skills (from the canonical skills taxonomy) with self-reported level
- career goal and career milestones
- application status counts
- an explicit disclaimer

No free-form narrative blob is assembled for the model.

### Skill-gap analysis (`GET /gaps?opportunity_id=…`, `career.get_skill_gaps`)

Deterministic comparison against **one** posted opportunity (requirements from
`opportunity_requirements` + the skills taxonomy) or, when no opportunity is
given, the candidate's stated career goal:

- matched skills, partial skills (candidate holds a related skill), missing
  skills
- skill coverage percentage
- experience gap and credential gap statements
- an understandable summary + disclaimer

The model cannot add or remove requirements; the service output is the only
source of the gap list.

### Career paths (`GET /paths`, `career.get_career_paths`)

Advisory steps drawn from the canonical career-path/career-path-step
infrastructure, classified against the candidate's **held history** (roles they
have actually held) versus their **stated goal**:

- `direct` — a path whose target the candidate has already held or is on
- `adjacent` / `transition` / `exploratory` — increasingly speculative labels,
  never presented as guaranteed outcomes

A candidate whose *goal* names the path target but whose *history* does not
include it is never labelled `direct` (regression-tested).

### Opportunity recommendations (`GET /opportunities?mode=…`, `career.get_recommendations`)

Explainable opportunities in the four canonical matching modes:
`strong`, `potential`, `transition` (career_transition), `explore`. Each
recommendation includes structured reason factors, e.g.:

- matched core skills (count of the requirement list covered)
- partial/missing skills
- experience-level compatibility
- career-path relationship between the candidate's history/goal and the role
- location/work-mode compatibility where the canonical data supports it

No salary or market statistics are invented — if the platform does not know, it
says so.

### Application analysis (`GET /applications`, `career.get_application_analysis`)

Deterministic read of the candidate's **own** application history:

- counts by status (applied/under review/interviewing/offer/rejected/
  withdrawn)
- recent application timeline
- response pattern summary

Never exposes other candidates, employer-private notes, or internal
deliberation content.

### Action plan (`GET /action-plan`, `career.get_action_plan`)

Suggestion-only, derived from the digest + goal: recommended skills to build,
milestones to set, roles to target, profile improvements. The plan is advice —
nothing in it mutates state. Milestone *creation* happens only through the
canonical milestone service with the candidate's explicit action
(`career.create_milestone`, LOW_RISK_WRITE).

## Data boundaries

| Data | In digest/context? |
|---|---|
| skills / experience / education / credentials / goals | Yes (whitelisted) |
| application status counts | Yes (aggregates only) |
| contact details, phone, email | No |
| government IDs, passport, tax ID | No |
| KYC state or documents | No |
| document contents | No |
| private messages / recruiter notes | No |

## Route list

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/career-advisor/digest` | structured professional digest |
| GET | `/api/v1/career-advisor/gaps` | gap analysis vs opportunity or goal |
| GET | `/api/v1/career-advisor/paths` | advisory career paths |
| GET | `/api/v1/career-advisor/opportunities` | recommendations, 4 modes |
| GET | `/api/v1/career-advisor/applications` | own application analysis |
| GET | `/api/v1/career-advisor/action-plan` | suggestion-only action plan |

All routes are authenticated, resolve the caller's PersonProfile server-side,
and are jobseeker/self-scoped only.
