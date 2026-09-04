# Phase 16 — Testing

All Phase-16 tests are deterministic: the structured facts are validated
independently of any LLM, and the suite runs with `AI_PROVIDER=none`.

## New test suite

`backend/tests_phase3/test_ai_interview_phase16.py` — 24 tests.

### Employer configuration & tenant grounding
| Test | Proves |
|---|---|
| `test_create_requires_org_permission` | non-member and wrong-role users get 403 |
| `test_create_requires_anchor_and_tenant_match` | missing anchor → 422; opportunity from another org → 403 |
| `test_entry_token_returned_once_and_stored_hashed` | plaintext returned once; DB stores SHA-256 only |
| `test_prohibited_configuration_rejected` | competencies touching protected topics → 422 |

### Candidate entry security
| Test | Proves |
|---|---|
| `test_claim_wrong_token_and_wrong_person_denied` | wrong token → 403; other person with real token → 403 |
| `test_missing_entry_token_header_rejected` | 401 without X-Interview-Token |
| `test_consent_required_before_start` | start before consent fails; consent → ready → in_progress |
| `test_consent_withdrawal_stops_session` | withdrawal cancels the session; no further progress |

### Question plan & flow
| Test | Proves |
|---|---|
| `test_plan_grounded_in_requirements_and_candidate` | plan count matches config; requirement text present; no prohibited topic in any question |
| `test_question_sequence_and_repeat_no_penalty` | sequence advances; repeat rephrases with no evaluation row |
| `test_answer_evaluation_never_persists_raw_answer` | raw answer absent from ALL ai_interview_* tables; dimensions 1–5 |
| `test_adaptive_followup_stays_linked_to_competency` | low-evidence answer yields a follow-up bound to the same competency |
| `test_invalid_state_transitions_rejected` | complete/pause before start, start-after-complete → 422 |
| `test_lazy_expiry` | past `expires_at` → claim returns expired (no scheduler) |
| `test_time_budget_ends_gracefully` | past duration → next-question completes and writes a report |

### Cross-tenant isolation
| Test | Proves |
|---|---|
| `test_employer_cross_org_isolation` | org B employer cannot view or read org A's session/report (403) |
| `test_candidate_cannot_read_employer_report` | candidate → employer report route → 403 |
| `test_concurrent_candidate_sessions_isolated` | two live candidate sessions cannot cross-act |

### Reports & decisions
| Test | Proves |
|---|---|
| `test_full_flow_report_and_decision` | full lifecycle; report marked human-review-required; candidate feedback has no decision content; employer decision recorded; invalid decision → 422 |
| `test_decision_requires_completed_interview` | decision before completion → 422 |

### Integrity & capability absence
| Test | Proves |
|---|---|
| `test_integrity_signals_are_signals_only` | signal recorded; facial/emotion signal type rejected; no evaluation side effect |
| `test_integrity_signals_bounded` | limit enforced (50) |
| `test_lifecycle_audited` | created/invited/consent/started/plan actions audited; no answer content in payloads |
| `test_facial_and_lie_topics_have_no_route_or_tool` | no /api/v1 route contains facial/lie/emotion concepts |

## Regression results

| Suite | Passed | Failed | Skipped |
|---|---|---|---|
| Canonical backend (SQLite) | **219** | 0 | 11 (PG-only RLS, by design) |
| PostgreSQL RLS suite | **11** | 0 | 0 |
| New Phase-16 tests | **24** | 0 | 0 |

## PostgreSQL validation

- Migration 0013 upgrade → downgrade → re-upgrade clean on PostgreSQL 16
  (72 public tables; alembic_version 0013).
- App-role grants re-run: 284 = 71 canonical tables × 4 DML.
- 11/11 RLS tests pass with migration 0013 applied.
- End-to-end PG smoke (`PG_SMOKE_PASS`): employer creates + invites →
  candidate claims (consent_required) → consent → start (AI-interview
  disclosure) → 3 answers → complete → employer report → human decision →
  cross-org isolation (403).

## Frontend

- Typecheck: clean. Lint: clean (no new warnings). Production build: green;
  `/jobseeker/ai-interview` and `/employer/ai-interviews` in the route
  manifest.

## Legacy compatibility

Legacy Careers backend untouched; imports cleanly at 107 routes. Canonical
`/api/v1` routes: **232** (213 + 19).
