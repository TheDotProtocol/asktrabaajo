# CURSOR WAVE 6 — FIGMA → IMPLEMENTATION MAPPING

Figma sources (opened via Figma MCP 2026-09-05):

| Portal | File | Key |
|---|---|---|
| Candidate | [asktrabaajo — Candidate](https://www.figma.com/design/AvJb5GfMmbhR0vgQW9pLUO/asktrabaajo---Candidate) | `AvJb5GfMmbhR0vgQW9pLUO` |
| Employer | [AskTrabaajo — HR](https://www.figma.com/design/TWxgrQJPdyGSsbTkM8gX1b/AskTrabaajo---HR) | `TWxgrQJPdyGSsbTkM8gX1b` |
| Super Admin | [Super Admin Platform](https://www.figma.com/design/M3U75YGTGthQFUJA9azs7w/AskTrabaajo-%E2%80%94-Super-Admin-Platform) | `M3U75YGTGthQFUJA9azs7w` |
| Government | [Government Portal](https://www.figma.com/design/IGQTJOpvt7odmdHjLazDDA/AskTrabaajo---Government-Portal) | `IGQTJOpvt7odmdHjLazDDA` |
| Athena | none | uses Candidate/Employer OS |

Classifications: EXACT · CLOSE · PARTIAL · MISSING · NOT APPLICABLE · BACKEND-LIMITED

Visual match is from **Figma MCP screenshots + Playwright localhost captures**. No automated pixel-diff overlay. **Not claimed pixel-perfect.**

## Candidate (`AvJb5GfMmbhR0vgQW9pLUO`)

| Figma screen | Route | Component | Impl | Visual | Functional | Discrepancies | Action |
|---|---|---|---|---|---|---|---|
| asktrabaajo-sign-in `9:73` | `/login` | `AuthSplit` + login form | yes | CLOSE | PASS | Figma copy differs slightly; Remember me is local-only (no session API) | Wave 6 restyle done |
| asktrabaajo-sign-up `9:6` | `/register` | `AuthSplit` + register | yes | CLOSE | PASS | Compact jobseeker/employer intent (Figma has no role picker). Government not self-serve | keep |
| asktrabaajo-home `5:6` | `/jobseeker` | `CandidateShell` + dashboard | yes | CLOSE | PASS | Figma is populated; DEV empty state is honest. No top search | none (no fake metrics) |
| asktrabaajo-work-id `5:211` | `/id/work-id` | Work ID page | yes | CLOSE | PASS | Same shell; Figma shows richer completed identity | none |
| asktrabaajo-athena `5:427` | `/jobseeker/athena` | `AthenaWorkspace` | yes | CLOSE | PASS | Figma shows a chat product; live is degraded-honest (`AI_PROVIDER=none`) | BACKEND-LIMITED chat |
| asktrabaajo-work-dna `5:769` | `/jobseeker/work-dna` | Work DNA page | yes | CLOSE | PASS | empty assessment | none |
| asktrabaajo-career-map `5:984` | `/jobseeker/career` | Career page | yes | PARTIAL | PASS | Figma map art vs Advisor/goals/paths cards | BACKEND-LIMITED map viz |
| asktrabaajo-career-development `5:2091` | `/jobseeker/career` | same | yes | PARTIAL | PASS | combined into Career | none |
| asktrabaajo-opportunities `5:1129` | `/jobseeker/opportunities` | Opportunities | yes | CLOSE | PASS | empty catalogue in DEV sqlite | none |
| asktrabaajo-applications `5:1346` | `/jobseeker/applications` | Applications | yes | CLOSE | PASS | empty | none |
| asktrabaajo-interviews `5:1618` | `/jobseeker/interviews` | Interviews | yes | CLOSE | PASS | empty | none |
| asktrabaajo-offers `5:1753` | `/jobseeker/offers` | Offers | yes | CLOSE | PASS | empty | none |
| asktrabaajo-credentials `5:1893` | `/jobseeker/credentials` | Credentials | yes | CLOSE | PASS | empty | none |
| asktrabaajo-settings `5:2756` | `/jobseeker/privacy` + `/id` | Privacy / account | yes | PARTIAL | PASS | split across two routes | none |
| asktrabaajo-skills-intelligence `5:2256` | — | — | no | MISSING | BACKEND-LIMITED | no dedicated skills-intel API/page | do not fake |
| asktrabaajo-compensation `5:2436` | — | — | no | MISSING | BACKEND-LIMITED | | do not fake |
| asktrabaajo-onboarding `5:2599` | — | — | no | MISSING | BACKEND-LIMITED | | do not fake |
| asktrabaajo-user-profile `9:142` | `/id/work-id` | Work ID | yes | PARTIAL | PASS | profile is Work ID, not a separate social profile | none |
| component-library / typography / handoff | — | tokens in `globals.css` + `candidate/ui` | reference | NOT APPLICABLE | — | | — |

## Employer (`TWxgrQJPdyGSsbTkM8gX1b`)

| Figma screen | Route | Component | Impl | Visual | Functional | Discrepancies | Action |
|---|---|---|---|---|---|---|---|
| employer-command-center `3:8` | `/company` | `EmployerShell` + dashboard | yes | PARTIAL | PASS | Figma has 65px search topbar + Athena prompt band. Implementation is 240px sidebar OS (same family as Candidate). Empty metrics honest | do not invent search/AI bar |
| athena-hr-command `3:188` | `/company/athena` | `AthenaWorkspace` | yes | CLOSE | PASS | degraded, no fake HR chat | none |
| workforce-intelligence `3:352` / employee-directory `3:4118` | `/company/members` | Members | yes | PARTIAL | PASS | members/RBAC, not a workforce intelligence product | BACKEND-LIMITED |
| job-creation `3:1219` | `/company/jobs/new` | Job draft wizard | yes | CLOSE | PASS | | none |
| Jobs nav | `/company/jobs` | Jobs list | yes | CLOSE | PASS | no `/jobs/[id]` or edit route | document |
| talent-pool / candidate-search / talent-intelligence | `/company/candidates` | Talent Graph | yes | PARTIAL | PASS | three Figma screens → one API-backed list | none |
| candidate-profile `3:1782` | `/company/candidates/[id]` | Candidate profile | yes | CLOSE | exists | not captured (no candidate in DEV) | NOT TESTABLE populated |
| recruitment-pipeline `3:2143` | `/company/pipeline` | Pipeline | yes | CLOSE | PASS | empty | none |
| interview-center / scheduling | `/company/interviews` | Interviews | yes | PARTIAL | PASS | no separate scheduling product | BACKEND-LIMITED |
| ai-interviewer-config / interview-results | `/employer/ai-interviews` | AI interviews | yes | PARTIAL | PASS | config+results combined | none |
| offer-center `3:3622` | `/company/offers` | Offers | yes | CLOSE | PASS | empty | none |
| hr-analytics `9:469` | `/company/analytics` | Analytics | yes | CLOSE | PASS | honest zeros | none |
| notifications `9:2969` | `/company/notifications` | Notifications | yes | CLOSE | PASS | empty | none |
| settings / security-center | `/company/settings`, `/id` | Settings | yes | PARTIAL | PASS | | none |
| employer-brand / company-work-id | `/company/profile` | Profile | yes | PARTIAL | PASS | offices/departments not first-class APIs | BACKEND-LIMITED |
| onboarding, performance, learning, compensation-intelligence, KYC viewer, command-palette, tasks, approvals | — | — | no | MISSING | BACKEND-LIMITED | no product APIs | do not fake |

## Super Admin (`M3U75YGTGthQFUJA9azs7w`)

| Figma screen | Route | Component | Impl | Visual | Functional | Discrepancies | Action |
|---|---|---|---|---|---|---|---|
| super-admin-command-center `3:6` | `/admin` | `AdminShell` + command center | yes | PARTIAL | PASS | Figma 250px + search topbar + megamenu. Live: 240px, Development badge, permission-filtered control-plane nav, honest zeros | BACKEND-LIMITED megamenu |
| audit-log `9:364` | `/admin/governance/audit` | Audit page | yes | CLOSE | PASS | metadata filters only | none |
| role-permissions `9:688` | `/admin/settings` | granted permissions list | yes | PARTIAL | PASS | cannot escalate; no role editor | BACKEND-LIMITED |
| finance-dashboard / transactions-ledger / billing-management | `/admin/finance` | Finance page | yes | PARTIAL | PASS | one finance surface vs three Figma screens; empty DEV | none |
| notification-center `10:6` | `/admin/notifications` | Notifications | yes | CLOSE | PASS | caller-scoped | none |
| system-status `11:245` | `/admin/operations` | Operations | yes | PARTIAL | PASS | honest “no status API” for payments/rate limits | BACKEND-LIMITED |
| athena-ai-operations `3:4752` | `/admin/athena` | Athena honesty | yes | BACKEND-LIMITED | PASS | no platform tools | none |
| customer-support / tech-support | `/admin/support` | Support honesty | yes | BACKEND-LIMITED | PASS | no ticket API | none |
| user-management / user-360 / company-360 / recruiter / jobs / applications / interviews / credentials / governments / marketing / campaign / analytics-center | — | — | no | MISSING | BACKEND-LIMITED | no platform directory APIs | do not fake |

Governance / enforcement / appeals / teams are **implemented** and visually in the Admin shell. They do not have dedicated Figma frames in the Super Admin file (those workflows came from backend Phase 10–11). Mapped to Control Plane nav, not fictional Figma screens.

## Government (`IGQTJOpvt7odmdHjLazDDA`)

| Figma | Route | Status |
|---|---|---|
| Government Portal (all frames) | none | **MISSING / BACKEND-LIMITED** — architecture only. No citizen UI. |

## Athena (no Figma)

Wave 4 OS design. Candidate and Employer workspaces visually verified in degraded mode. Not redesigned in Wave 6.
