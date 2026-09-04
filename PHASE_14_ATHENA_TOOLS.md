# PHASE 14 — ATHENA TOOL REGISTRY

Status: IMPLEMENTED — 26 tools, all mapped 1:1 to existing canonical services
(`applications`, `matching`, `talent`, `communications`, `outreach`,
`company_os`). No tool invents new business behavior. Registry:
`backend/app/services/athena_tools.py`.

## Tool contract

Every tool declares (enforced by the registry hygiene test):

- `name`, `description` (surface for the provider)
- `input_model` (Pydantic schema — validated BEFORE authorization/execution and
  used to generate the provider JSON schema)
- `modes` — which Athena modes may invoke it
- `permission` — org-scoped RBAC permission code required (None = own-data tool)
- `risk` — `read_only` | `low_risk_write` | `high_risk_write`
- `read_only`, `data_scope` (`own` | `org` | `public`), `consent_required`,
  `confirmation_required`, `audit_required`

## Registry

### Jobseeker (own data / public discovery)

| Tool | Risk | Data scope | Permission |
|------|------|-----------|------------|
| get_my_work_id | read_only | own | — |
| get_my_skills | read_only | own | — |
| get_my_credentials | read_only | own | — |
| get_my_career_goals | read_only | own | — |
| get_my_applications | read_only | own | — |
| get_my_interviews | read_only | own | — |
| get_my_offers | read_only | own | — |
| get_application_status | read_only | own | — |
| list_conversations | read_only | own | — |
| get_conversation | read_only | own | — |
| search_opportunities | read_only | public | — |
| get_opportunity | read_only | public | — |
| compare_opportunities | read_only | public | — |
| save_opportunity | low_risk_write | own | — |
| apply_to_opportunity | **high_risk_write** | own | — |

### Employer / recruiter (org-scoped, permission-gated)

| Tool | Risk | Data scope | Permission |
|------|------|-----------|------------|
| search_talent | read_only | org | candidates.search |
| get_candidate | read_only | org | candidates.read |
| match_candidates_for_opportunity | read_only | org | candidates.search |
| get_org_jobs | read_only | org | jobs.view |
| get_org_application_status | read_only | org | applications.view |
| summarize_org_applications | read_only | org | applications.view |
| list_org_conversations | read_only | org | communications.read |
| get_org_conversation | read_only | org | communications.read |
| draft_message | read_only | org | communications.read |
| send_message | **high_risk_write** | org | communications.send |
| create_outreach | **high_risk_write** | org | talent.outreach.create |

Government and platform-operator modes expose **zero tools** in this release
(architecture-only).

## High-risk semantics

`high_risk_write` tools never execute on the model's say-so. The orchestration
layer creates an `athena_action_confirmations` row bound to the exact canonical
scope (SHA-256 over canonicalized args), returns it as
`pending_confirmations`, and stops the loop. Execution happens only when the
owning user approves via `POST /athena/confirm` and the stored scope
re-validates + re-authorizes at that moment. Denying or letting the 15-minute
TTL lapse records the decision; wrong-object scopes require a new confirmation.

## Guarantees proven by tests

- Unknown/arbitrary tools (`run_sql`, `fetch_url`, `read_file`,
  `execute_shell`) are refused + audited.
- A candidate cannot invoke employer tools; an employer cannot invoke
  candidate-private tools; an org cannot reach another org's application via a
  tool even knowing the UUID.
- Permission-less roles (e.g. `hiring_manager` without
  `talent.outreach.create`) are denied and nothing is created.
- Malformed tool arguments are rejected before authorization/execution.
- Confirmation for object A never authorizes object B.
- Registry hygiene: every tool has a schema, risk class, modes, and matching
  registry key.
