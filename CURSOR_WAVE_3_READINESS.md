# CURSOR WAVE 3 READINESS — Employer / Company OS + Figma

**Status:** PLAN ONLY. Do not implement until a separate Wave 3 approval prompt.  
**Depends on:** Wave 2 closed (`CURSOR_WAVE_2_CLOSURE.md`). Wave 1 remains the auth/RBAC foundation.

Wave 3 builds the **Employer Employment OS** the same way Wave 2 built the Candidate OS: Figma shell + canonical `/api/v1` + empty states + no invented production data.

---

## Recommended sequence

| # | Slice | Current UI | Backend | Notes |
|---|---|---|---|---|
| 1 | Employer shell | `OsChrome` / company layout | `/auth/me`, org membership | Reuse `OrgProvider` + `PortalGuard`. Do not invent org context |
| 2 | Company dashboard | `/company` | `/company/{org}/dashboard` | Real pipeline counts only |
| 3 | Jobs / opportunities | `/company/jobs` | `/company/{org}/jobs`, opportunities | Approval + status from backend |
| 4 | Pipeline | `/company/pipeline` | `/company/{org}/applications` | Controlled state machine |
| 5 | Candidate view | `/company/candidates/[id]` | talent + disclosure | **No raw document dump**; grants only |
| 6 | Interviews | company interview pages | `/company/{org}/interviews` | No facial/lie UI |
| 7 | Offers | (thin) | `/company/{org}/offers` | Company issues; candidate decides |
| 8 | Communications | `/company/communications` | outreach + conversations | Candidate acceptance gate |
| 9 | Billing | `/employer/billing` | `/billing/*` | Read-only self-service; mock provider |
| 10 | AI Interview (employer) | `/employer/ai-interviews` | `/ai-interviews/*` | Human decision required |
| 11 | Empty / loading / error | mixed | error envelope | Same Candidate-quality empty states |
| 12 | Cross-tenant QA | tests exist | 403/404 | Must stay green |

**Out of Wave 3:** Athena chat (Wave 4), Government, Super Admin Figma, hosted live migrate unless a new one-line authorization is given, production deploy, push.

---

## Execution rules

- Consume `/api/v1` through `frontend/src/lib/api/`.
- Do not replace Wave 1 session handling.
- Do not flatten Candidate OS or Legacy Careers.
- Keep `AI_PROVIDER=none` and `PAYMENT_PROVIDER=mock` honest.
- Tenant isolation is backend-authoritative.

## Database

Same classification as Wave 2: hosted project is pre-launch demo; **do not write to it from the laptop `.env` unless the owner sends an explicit live-reconciliation line**. Prefer isolated sqlite / scratch Postgres.

## Public website

Still a separate repo. CTA wiring remains an operator/website change, not Wave 3 unless requested.
