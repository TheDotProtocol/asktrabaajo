# CURSOR WAVE 4 READINESS — Athena product UI

**Status:** PLAN ONLY. Do not implement until a separate Wave 4 approval prompt.  
**Depends on:** Wave 3 closed (`CURSOR_WAVE_3_CLOSURE.md`).

Wave 4 is **Athena chat** for Candidate and Employer, using existing `/api/v1/athena/*` tools and **exact-scope confirmation** for high-risk actions.

---

## Recommended slices

| # | Slice | Backend | Rule |
|---|---|---|---|
| 1 | Candidate Athena room | `/athena/sessions`, messages, tools | No fake chat if `AI_PROVIDER=none` |
| 2 | Employer Athena HR | same | Org-scoped tools only |
| 3 | Confirmation UI | `POST /athena/confirm` | Exact IDs; never auto-confirm |
| 4 | Tool / usage display | usage routes | Honest degraded mode |
| 5 | Batch apply / outreach confirmations | existing high-risk tools | Reuse Wave 2 exact-count pattern |
| 6 | Audit of what Athena can see | digest whitelist | No extra PII |

**Out of Wave 4:** Government, Super Admin Figma, hosted live migrate, production deploy, push, autonomous hiring.

## Rules

- Do not replace Wave 1 session, Wave 2 Candidate OS, or Wave 3 Employer OS.
- Do not invent tools that are not registered in the Athena catalog.
- Keep `AI_PROVIDER=none` honest.
- Hosted DB: same Wave 2/3 policy — isolated sqlite unless a genuine hosted write is documented first.
