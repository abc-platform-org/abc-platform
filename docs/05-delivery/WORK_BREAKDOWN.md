# Work Breakdown Structure — ABC-WBS-001

All work packages are **proposed**; checkboxes indicate planning scope, not completed execution. Link each task to a GitHub issue after repository access is available.

## Work-package definition

Each WP: `{wp_id, phase, task, parent_features, engine_owner, dependencies, deliverable_paths, acceptance_tests, risks, reviewer_role, evidence_url, status}`.

## Initial executable backlog (sequential)

| WP | Phase | Deliverable | Prerequisite | Exit evidence |
|---|---|---|---|---|
| WP-000-01 | 00 | Source archive and authority table | Accessible sources | Versioned inventory |
| WP-000-02 | 00 | Migration conflict review | WP-000-01 | Conflict decisions or explicit open status |
| WP-000-03 | 00 | Defects/gaps register | WP-000-01 | Severity & owner |
| WP-001-01 | 01 | Feature/PRD crosswalk | WP-000-02 | Coverage check |
| WP-001-02 | 01 | Shared-screen journeys | WP-001-01 | Walkthrough review |
| WP-001-03 | 01 | Service release matrix | WP-001-01 | Scope decisions |
| WP-002-01 | 02 | Engine boundaries/contracts | WP-001-01 | Contract test stubs |
| WP-002-02 | 02 | Data and event schema | WP-002-01 | Schema validation |
| WP-002-03 | 02 | ADR/threat model | WP-002-01 | Reviews |
| WP-003-01 | 03 | Shared AI Studio UX prototype | WP-001-02 | Scenario UX tests |
| WP-003-02 | 03 | Specialist Technical Plan UI | WP-002-01 | Role-boundary review |
| WP-004-01 | 04 | Auth/Tenant/Consent | WP-002-03 | Security tests |
| WP-004-02 | 04 | Durable session and jobs | WP-002-02 | Crash/resume tests |
| WP-004-03 | 04 | Evaluation harness | WP-002-01 | Reproducible suite execution |
| WP-005-01 | 05 | Service QuestionProfileRegistry | WP-001-03 | Consultation question suite |
| WP-005-02 | 05 | Adaptive selector and stopping policy | WP-005-01 | Expert question evaluation |
| WP-006-01 | 06 | Knowledge/ontology migration | WP-000-02 | ID / source reconciliation |
| WP-006-02 | 06 | Evidence/decision/look specification | WP-006-01 | Grounding & regression tests |
| WP-007-01 | 07 | Image input and masks | WP-004-02 | Region labels and mask metrics |
| WP-007-02 | 07 | Generation/compositing | WP-007-01 | Pixel tests |
| WP-007-03 | 07 | Visual QA/benchmark | WP-007-02 | Human + automated evidence |
| WP-008-01 | 08 | Immutable version graph | WP-007-03 | Revision tests |
| WP-008-02 | 08 | Compare/try-on/inspiration UI | WP-008-01 | E2E visual flows |
| WP-009-01 | 09 | SOP protocol registry and graph | WP-001-03 | Specialist validation of SOP |
| WP-009-02 | 09 | Plan generation/feasibility | WP-009-01 | TEC test suite |
| WP-009-03 | 09 | Authenticated specialist approval | WP-009-02 | Invalidation and audit tests |
| WP-010-01 | 10 | CRM/calendar/team/service core | WP-004-01 | Transaction tests |
| WP-010-02 | 10 | POS/inventory/analytics/business actions | WP-010-01 | Ledger/permissions tests |
| WP-011-01 | 11 | Shared-session end-to-end | WP-009-03, WP-010-01 | Traceable E2E proof |
| WP-012-01 | 12 | Golden + visual/technical/security | WP-011-01 | Signed evidence review |
| WP-013-01 | 13 | Controlled release/rollback | WP-012-01 | Pilot and rollback record |
| WP-014-01 | 14 | Advanced service pack releases | WP-013-01 | Per-pack QA and specialist gate |
| WP-015-01 | 15 | International SaaS validation | WP-014-01 | Market gate results |

## Parallel execution guidance

A product/UX owner may build prototype designs while platform engineering develops Phase 04, once Phase 02 contracts are stable. Business OS core may proceed independently from image worker development. CI, security, quality and documentation are continuous. Interface changes require versioning and consumer sign-off. Define CODEOWNERS only after real maintainers are known.
