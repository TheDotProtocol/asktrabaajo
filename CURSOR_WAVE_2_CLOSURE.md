# CURSOR WAVE 2 CLOSURE — Jobseeker Employment OS

**Status:** IMPLEMENTED (local, unpushed)  
**Depends on:** Wave 1 ACCEPTED (`1ecf8be`)  
**Figma:** [asktrabaajo — Candidate](https://www.figma.com/design/AvJb5GfMmbhR0vgQW9pLUO/asktrabaajo---Candidate) (`AvJb5GfMmbhR0vgQW9pLUO`)  
**Hosted database:** **UNTOUCHED** (see `CURSOR_WAVE_2_DB_CLASSIFICATION.md`)

Wave 2 turns the Candidate portal into a real client of `/api/v1` inside the Candidate Figma shell. Wave 1 auth, refresh, PortalGuard, OrgProvider, and the API client were not replaced.

---

## 1. What was implemented

- Candidate application shell (`CandidateShell`): 240px sidebar, gold/black brand, mobile drawer, unread badge, Athena marked Soon
- Dashboard from `GET /jobseeker/dashboard` — real counts, polished empty states, no invented production stats
- Work ID restyled and complete: profile, experience, education, employment, skills, credentials, documents, truthful verification pills
- Documents vault + employer request approve/decline
- Credentials list with verified / pending / unverified / expired / revoked
- Work DNA assessment + dimensions (no protected-characteristic inference)
- Career goals, milestones, Career Advisor snapshot, intelligence, plus `/career-advisor/{gaps,paths,opportunities,action-plan}`
- Opportunities: catalogue search + modes `strong` / `potential` / `transition` / `explore` (backend `transition` = career transition)
- Explicit apply confirmation; batch apply requires typing the selected count and posts exact IDs
- Applications tracker with Applied → … → Onboarding pipeline and real timeline
- Interviews + reschedule (backend policy); links to AI Interview and Interview Prep
- Offers accept/decline via backend decision
- Communications (existing API; candidate acceptance gate unchanged)
- Notifications center + header badge (`{ unread }`)
- Settings / privacy in human language; `/id` security & sessions
- Athena entry is honest: no fake chat

## 2. Figma screens mapped

| Frame (approx.) | Route | API |
|---|---|---|
| Home `5:6` | `/jobseeker` | `/jobseeker/dashboard` |
| Work ID `5:211` | `/id/work-id` | `/work-id/*` |
| Athena `5:427` | `/jobseeker/athena` | Honest entry only (Wave 4 chat) |
| Work DNA `5:769` | `/jobseeker/work-dna` | `/jobseeker/work-dna*` |
| Career map `5:984` / development `5:2091` | `/jobseeker/career` | `/jobseeker/advisor`, `/goals`, `/milestones`, `/career/intelligence`, `/career-advisor/*` |
| Opportunities `5:1129` | `/jobseeker/opportunities`, `[id]` | `/jobseeker/opportunities*`, `/career-advisor/opportunities` |
| Applications `5:1346` | `/jobseeker/applications` | `/jobseeker/applications*` |
| Interviews `5:1618` | `/jobseeker/interviews` | `/jobseeker/interviews*` |
| AI Interview / Prep | `/jobseeker/ai-interview`, `/interview-prep` | `/ai-interviews/*`, `/interview-prep/*` |
| Offers `5:1753` | `/jobseeker/offers` | `/jobseeker/offers*` |
| Credentials `5:1893` | `/jobseeker/credentials` | `/work-id` credentials |
| Documents (disclosure) | `/jobseeker/documents` | `/documents`, `/jobseeker/document-requests` |
| Settings `5:2756` | `/jobseeker/privacy`, `/id` | `/work-id/privacy`, `/auth/*` |
| Notifications / messages | `/jobseeker/notifications`, `/communications` | matching jobseeker routes |

## 3. APIs connected

All through `frontend/src/lib/api/` (`session.ts` → `ApiClient`). No mock APIs, no second matcher.

New TypeScript types only: Career Advisor digest/gaps/paths/opportunities/action-plan, documents, privacy.

## 4. Database changes

**None on hosted PostgreSQL.**

Classification: `CURSOR_WAVE_2_DB_CLASSIFICATION.md`.

## 5. Was the development DB rebuilt?

**No hosted rebuild.** Isolated sqlite (`scripts/wave2_candidate_e2e.py`) creates the canonical schema in-process with `dev+…@asktrabaajo.local` users. Alembic `0001`–`0014` were not modified.

Reason: `backend/.env` still points at the shared hosted project. A rebuild from this laptop would be a live write. Wave 2 UI does not require that write.

## 6. What remains

- Athena full chat + tool confirmations (Wave 4)
- Employer Figma OS (Wave 3)
- MFA enroll polish (Wave 9)
- Hosted schema reconciliation (operator; optional now that data is demo-only)
- Public website CTAs still point at marketing-SPA placeholders
- Communications visual polish is thinner than Figma (API complete)
- Interview Prep still text-first; answers not persisted unless backend already does

## 7. What is genuinely blocked

- Real AI / voice / video providers (`AI_PROVIDER=none` stays honest)
- Real payments (`PAYMENT_PROVIDER=mock`)
- Remote staging project (not provisioned)
- Production deploy / push (out of scope)
- Government / Super Admin Figma

PITR / live reconciliation is **no longer a Wave 2 product blocker**. It remains an **operator** action if they want the hosted project to match Alembic.

## 8. Ready for Wave 3

Yes — Employer / Company Employment OS on the same Wave 1 foundation and this Candidate shell pattern.

Do not start Wave 3 until a separate approval prompt.
