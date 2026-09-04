# Athena design decisions (Wave 4)

There is no Athena Figma. This document records the authorized design so Wave 5 does not reinvent it.

## 1. Why there was no Athena Figma

Athena is an intelligence layer over existing OS products. The owner authorized Cursor to design it from the Candidate and Employer implementations (`#0b0c0d`, `#111315`, gold `#d4af37`, 240px shells, shared `candidate/ui` primitives).

## 2. Design system used

Reused: typography, cards, gold/black borders, `PageHeader`, `StatusPill`, `btnCls` / `ghostBtnCls`, `inputCls`, empty/error states. No second visual identity. No ChatGPT clone, neon, or sparkle chrome.

## 3. Information architecture

- **Global workspace:** `/jobseeker/athena` and `/company/athena` share `AthenaWorkspace`.
- **Contextual entry:** `?from=` allowlist only (`career`, `opportunities`, `pipeline`, …). Purpose is a short backend session string — not a client digest.
- **Task Athena:** “Ask Athena” links from Career, Opportunities, Pipeline, Talent Graph.

One product, two modes (`jobseeker` / `employer`). Government/platform modes are not presented as working products.

## 4. Global vs contextual

The workspace is the conversation surface. Context is a rail (current surface + OS links + registered capability names). Contextual launch does not pass Work ID internals, contact data, or page state dumps.

## 5. Candidate Athena

Mode `jobseeker`. Suggested prompts map to registered tools (Career Advisor, opportunities, applications, interview prep). Results link back into Candidate OS. Athena does not rebuild Career Advisor.

## 6. Employer Athena

Mode `employer` with `organization_id` from `OrgProvider`. Suggested prompts map to Talent Graph, pipeline, jobs, interviews. Candidate privacy stays on the backend.

## 7. Action / confirmation UX

States stay distinct: information → proposed → confirming → executing → completed/failed. High-risk tools use `POST /athena/confirm` with exact `confirmation_id`. Buttons name the action (“Apply to 4 selected jobs”), never “Sure”.

## 8. Degraded provider

`GET /athena/status` reports `not_configured` when `get_provider()` is `None`. The composer is disabled. Deterministic OS links remain. `POST /athena/message` still returns `ai.provider_unavailable` — no fabricated reply.

## 9. Responsive design

Desktop: conversation + 288px rail. Mobile: stacked full-width workspace (not a shrunk desktop). Confirmation is a focused dialog.

## 10. Accessibility

Composer label, `aria-live` on the thread, dialog `aria-modal`, Escape cancels, visible gold focus, confirm button receives initial focus.

## 11. Backend APIs used

`GET /athena/status` (Wave 4, metadata only), `/modes`, `/tools`, `POST /session`, `POST /message`, `POST /confirm`, `GET /confirmations`, `POST /session/{id}/close`, `GET /usage`.

## 12. Backend gaps

- **No session list / message history API.** Current conversation is client-state for the active session. Not invented as persistence.
- **No provider name/model in status.** Intentional.
- **`GET /athena/status` added** so the UI can degrade without burning a chat turn.

## 13–14. Database

No Alembic changes. Hosted database **untouched**. Isolated sqlite E2E only.

## 15. Security validation

Wave 4 E2E: mode isolation, cross-tenant session denial, stolen session denial, unknown confirmation 404, unauthenticated 401, degraded chat has no `reply`. Phase 14 suite remains the confirmation/crypto suite of record.

## 16. Remaining limitations

Live chat requires `AI_PROVIDER=openai`. Session history is not a product feature yet. Recruiter uses the same employer workspace. Government Athena is architecture-only.

## 17. Wave 5 readiness

See `CURSOR_WAVE_5_READINESS.md`. Do not start until a separate approval prompt.
