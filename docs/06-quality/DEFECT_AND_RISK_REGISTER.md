# Architecture & Project Risk Register — Initial Audit

**These are documented conflicts / unimplemented obligations / risks, not claimed bugs observed in live code.** Verify through source inspection and actual tests.

| ID | Category | Finding / risk | Severity planning | Owner / action | Evidence |
|---|---|---|---|---|---|
| ABC-R01 | Baseline | Legacy GPT-only vs intended platform; newer productization references unresolved | High | Phase 00 source/ADR review | DOC-001/005/007 versions |
| ABC-R02 | Runtime | 10 legacy GPT roles are not independently deployed 19 engines | High | Implement explicit contracts and modular runtime | DOC-005 |
| ABC-R03 | Testing | 120 authored Golden Tests have no verified execution | High | Test harness / real runs | DOC-018 |
| ABC-R04 | Visual | Identity and region edits cannot be guaranteed by prompt | Critical | Segmentation + deterministic composite + QA | DOC-009 |
| ABC-R05 | Session | Lost context or stale async output corrupts consultation | High | Durable checkpoint/version lease tests | Proposed runtime |
| ABC-R06 | Access | UI-only specialist role could expose confidential records | Critical | Backend RBAC / shared screen design | Proposed UX |
| ABC-R07 | Tenant | Cross-salon/branch leakage possible absent isolation tests | Critical | Tenant-aware RLS/asset tests | Proposed SaaS |
| ABC-R08 | Safety | Prompt-only safety intercept is bypassable | Critical | Code policy gates + expert review | DOC-012 |
| ABC-R09 | Decision | Recommendations may vary or ignore customer constraint | High | Hard filter / regression suite | DOC-007 |
| ABC-R10 | Knowledge | Retrieval or ontology may mismatch service/attribute mapping | High | Content versioning / source checks | KB-900 |
| ABC-R11 | Ops | Missing traces/retries/permissions could produce fake operations | High | Outbox / telemetry / approval | Proposed |
| ABC-R12 | Visual repeat | Iterative edit destroys previously accepted state | Critical | Immutable version DAG and tests | AIS-015 |
| ABC-R13 | Privacy | Sensitive photo retention and cross-region compliance undefined | Critical | Consent/retention/legal review | Proposed |
| ABC-R14 | Technical | No reviewed service SOP could cause unsupported procedure instructions | Critical | SOP registry + validation | ENG-15 |
| ABC-R15 | Product | Fake dashboard KPIs mistaken for live evidence | High | Metric provenance; distinguish prototype | UI images |
| ABC-R16 | Deployment | Multiple teams overwrite `main` or change contracts ad hoc | High | PR reviews, branch protection, ADRs | Repo governance |
| ABC-R17 | Provider | AI latency/cost/identity quality unbenchmarked | High | Benchmark and provider abstraction | Visual pipeline |
| ABC-R18 | Service scope | Advanced services exposed before test/professional approval | Critical | Service release state and flags | Coverage matrix |

## Risk lifecycle

`OPEN → INVESTIGATING → CONFIRMED | NOT_REPRODUCIBLE → REMEDIATION_PLANNED → FIXED → TEST_VERIFIED → CLOSED`. Assign person and evidence URL after repo connection. Do not use fabricated SEV codes or dates as if incidents occurred.
