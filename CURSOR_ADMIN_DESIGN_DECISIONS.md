# Super Admin design decisions (Wave 5)

Figma: [AskTrabaajo — Super Admin Platform](https://www.figma.com/design/M3U75YGTGthQFUJA9azs7w/AskTrabaajo-%E2%80%94-Super-Admin-Platform) (`M3U75YGTGthQFUJA9azs7w`).  
Primary frame: Command Center `3:6`, sidebar `3:8`.

This is the internal control plane. It is **not** unrestricted database access.

## 1. Visual language

Reused Candidate / Employer OS tokens: `#0b0c0d` canvas, `#0d0e10` sidebar, `#111315` cards, gold `#d4af37`, 240px-class sidebar, shared `candidate/ui` primitives (`PageHeader`, `cardCls`, `btnCls`, `inputCls`). Lucide icons — Figma asset URLs are not used.

The Figma badge said Production. The product is pre-launch. The shell badge says **Development**.

## 2. Figma megamenu vs real APIs

Figma shows Overview, Global Intelligence, People, Companies, Recruiters, Jobs, Applications, Interviews, Work IDs, Credentials, Governments, Athena, Communications, Security, Analytics, Operations, plus Support / Tech / Marketing / Finance consoles.

Most of those screens have **no platform directory API**. They are **foundation / future** and are not fabricated.

Implemented nav (permission-filtered):

| Nav | Route | Permission / note |
|---|---|---|
| Command Center | `/admin` | any platform permission |
| Governance | `/admin/governance` | `reports.read` |
| Enforcement | `/admin/governance/enforcement` | `enforcement.read` |
| Appeals | `/admin/governance/appeals` | `appeals.read` |
| Audit | `/admin/governance/audit` | `platform.audit.read` |
| Teams | `/admin/governance/teams` | `reports.teams` |
| Support | `/admin/support` | honesty page; no ticket API |
| Finance | `/admin/finance` | `finance.read` / `finance.manage` |
| Operations | `/admin/operations` | caller-scoped events + honest provider gaps |
| Athena | `/admin/athena` | architecture-only; marked Soon |
| Notifications | `/admin/notifications` | caller-scoped |
| Settings | `/admin/settings` | own `/auth/me` + sessions |

## 3. Least privilege

`super_admin` is a platform role, not a frontend override of private data. Nav hides items the caller lacks. Backend 403 remains authoritative.

`PortalGuard allow="platform"` uses `canAccessPlatform()` (`reports.*` / `enforcement.*` / `appeals.*` / `finance.*` / `support.read` / `audit.read` / `users.read` / `sessions.manage` / `admin.manage`). Finance-only and support-only operators can open `/admin` and see only what they are allowed.

`homeForMe` sends platform-only users to `/admin`. An employer membership still wins so company admins are not dumped into Super Admin.

## 4. Command center

Cards are truthful counts from canonical APIs: governance dashboard, appeals `submitted` total, enforcement `proposed` total, finance available/none, caller events, Athena availability. No invented metrics. Empty state if the caller has no authorized signals.

## 5. Governance / enforcement / appeals

Existing Phase 10–11 pages, restyled into the OS shell. Lifecycle is unchanged: propose → approve → active → expire/revoke. Creator ≠ approver for severe types is **server-enforced**. The UI does not auto-reinstate; accepted appeals show the backend `superseding_action_id`.

## 6. Audit

`GET /governance/audit` only. Metadata filters that exist: action, action prefix, actor, organization, resource type/id (use for case / enforcement), result, request id, from/to. **Severity is not a first-class audit query** — documented, not faked. Payloads stay sanitized.

## 7. Users / organizations

`GET /organizations` returns the caller’s memberships. There is **no** platform user-search or org-directory API. No People / Companies console was built.

## 8. Support

`support.read` exists. Ticket / customer-360 routes do not. `/admin/support` explains case-linked access and links to governance only when `reports.read` is present.

## 9. Platform finance

`/api/v1/finance/*` only. Distinct from `/employer/billing` (`billing.manage`). Refund form requires `finance.manage`. Provider secrets are never shown.

## 10. Operations

Honest: Athena `GET /athena/status`; payments and rate limits have **no** operator status API; events are caller-scoped metadata. No infrastructure credentials.

## 11. Athena for Super Admin

`platform_operator` mode exists in architecture and has **no tools**. `/admin/athena` is unavailable / future. Candidate and Employer Athena were not replaced. No second AI service.

## 12. Notifications

`/jobseeker/notifications` + `/events`. No fabricated governance alert feed.

## 13. Unsupported Figma capabilities (do not build)

People directory · Companies directory · Recruiters · global Jobs/Applications/Interviews browsers · Work ID browser · Credentials browser · Governments / citizen intelligence · Marketing console · Global Intelligence · Security center beyond own sessions · Analytics megadashboard · Tech Support diagnostics · Customer Support tickets · live payment-processor health · rate-limit dashboard.

## 14. DEV fixtures

Wave 5 E2E uses isolated sqlite and emails prefixed `dev+wave5.*`. No hosted seed. Marked DEV in the script.
