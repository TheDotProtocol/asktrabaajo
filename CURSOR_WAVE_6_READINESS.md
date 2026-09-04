# CURSOR WAVE 6 READINESS

**Status:** PLAN ONLY. Do not implement until a separate Wave 6 approval prompt.  
**Depends on:** Wave 5 closed. This document does **not** authorize Wave 6.

Wave 5 delivered the Super Admin control plane. Wave 6 is the next UI-integration slice only if the owner approves it separately.

## Likely Wave 6 scope (proposal, not authorized)

From the original UI integration plan and remaining honest gaps:

- Communications polish (Candidate + Employer already API-backed; deepen empty/error/thread UX if needed)
- Commerce polish (employer billing entitlements/usage detail; still no client payment authority)
- MFA enroll polish on `/id` (backend exists)
- Athena session history **only if** a list API is added first — do not invent history
- Accessibility / keyboard pass across OS shells
- Public website CTA wiring in the **separate** marketing repo (not this application)

## Explicitly not Wave 6

- Government citizen products or individual lookup (forbidden)
- Platform-operator Athena tools / admin AI
- Figma People / Companies / Governments directories (no APIs)
- Support ticket product
- Hosted live database reconciliation or migrate
- Production deploy or push
- Legacy Careers rewrite
- Merging `TheDotProtocol/trabaajowebsite` into this repo

## Rules that remain

- Do not replace Waves 1–5.
- Do not invent APIs, metrics, or AI.
- `AI_PROVIDER=none` and `PAYMENT_PROVIDER=mock` stay honest.
- Hosted DB: isolated sqlite / scratch Postgres unless a hosted write is documented first.
- Least privilege remains mandatory.
- Do not touch production.
