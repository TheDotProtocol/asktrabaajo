# CURSOR WAVE 5 CLOSURE — Super Admin / Platform Operations

**Status:** IMPLEMENTED (local, unpushed)  
**Depends on:** Waves 1–4 (Wave 4 refinement `8800472`)  
**Figma:** [AskTrabaajo — Super Admin Platform](https://www.figma.com/design/M3U75YGTGthQFUJA9azs7w/AskTrabaajo-%E2%80%94-Super-Admin-Platform) (`M3U75YGTGthQFUJA9azs7w`)  
**Hosted database:** **UNTOUCHED**  
**Wave 6:** not started — see `CURSOR_WAVE_6_READINESS.md` (PLAN ONLY)

The Super Admin portal is now a real client of canonical governance, enforcement, appeals, audit, teams, finance, and events APIs. It is **not** unrestricted access to private candidate or employer data. Waves 1–4 were not replaced.

## 1. Implemented

- `AdminShell` — 240px sidebar, gold mark, Global Admin + Development badge, permission-filtered nav
- Command center at `/admin` — authorized counts only
- Governance queue + case detail (assign, priority, team, escalate, notes, links, SLA, signals)
- Enforcement queue + detail + propose form (lifecycle + creator ≠ approver)
- Appeals queue + detail (assign, review, decide, superseding reinstatement)
- Audit review with canonical filters (metadata only)
- Governance teams + members + workload
- Support honesty page (no ticket API)
- Platform finance (transactions, invoices, subscriptions, refunds)
- Operations (Athena status, honest payment/rate-limit gaps, caller events)
- Admin Athena unavailable / architecture-only
- Notifications + settings (own permissions and sessions)
- `canAccessPlatform` + `PortalGuard allow="platform"`

## 2. APIs

No new backend routes. Consumed existing `/api/v1` surfaces through `frontend/src/lib/api`. No mock admin APIs. No frontend AI. No automatic reinstatement.

## 3. Backend changes

**None.**

## 4. Database

- No Alembic changes
- No hosted writes
- Development hosted schema **not** rebuilt
- Isolated sqlite E2E only
- Local scratch Postgres `p14_test` used only for existing RLS suite

## 5. Security

- Candidate / employer cannot open Admin APIs (403)
- Finance cannot use governance controls
- Support cannot authorize refunds or assign cases
- Creator cannot approve own suspension
- Second enforcement manager can approve
- Appellant cannot see `review_note` on submit
- Candidate cannot read `/governance/audit`
- Audit payloads contain no password material
- Frontend permission checks are UX only

## 6. Tests

| Check | Result |
|---|---|
| `npx tsc --noEmit` | PASS |
| `npm run lint` | PASS — 0 errors, 5 pre-existing Careers warnings |
| `npm run build` | PASS |
| `pytest tests_phase3` | PASS (251 passed / 11 skipped without PG) |
| PostgreSQL RLS (`p14_test`) | PASS 11/11 |
| Wave 2 Candidate E2E | PASS |
| Wave 3 Employer E2E | PASS |
| Wave 4 Athena E2E | PASS |
| Wave 5 Super Admin E2E | PASS (`scripts/wave5_admin_e2e.py`) |
| Browser click-through | **Browser click-through not available.** |

Wave 5 E2E journey: DEV admin login → dashboard → candidate-filed case → assignment → enforcement proposal → approval boundary → second-operator activate → appeal → decision + superseding reinstatement → audit → finance/support/employer/candidate 403s.

## 7. DEV data

E2E registers `dev+wave5.*` users on isolated sqlite. No hosted seed. Clearly DEV-prefixed.

## 8. Remains / foundation

- Figma People / Companies / Governments / Marketing / Global Intelligence
- Support ticket product
- Platform-operator Athena tools
- User/org directory search
- Rate-limit and payment-provider status APIs
- MFA enroll polish
- Public website CTA wiring

## 9. Blocked

Hosted live migrate, production deploy, push, government citizen lookup, unrestricted private-data admin.

## 10. Wave 6

Ready as a **separate** approval only. Do not start from this closure. See `CURSOR_WAVE_6_READINESS.md`.
