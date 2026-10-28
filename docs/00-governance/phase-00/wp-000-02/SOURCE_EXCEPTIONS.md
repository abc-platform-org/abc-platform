# WP-000-02 — Missing Source Exception Proposals

**Important:** These are **requests for decision**, not approved exceptions. No `SOURCE_APPROVED` flag may be set automatically. Intended reviewers: Product Authority and Architecture Authority; QA reviews downstream implications.

| ID | Reference | Current state | Permitted interim use | Forbidden interim use | Approve only with | Owner role |
|---|---|---|---|---|---|---|
| SRC-EXC-001 | DOC-001 v1.2.0 | UNRECOVERED | Legacy DOC-001 v1.1.0 for matching behavior; current user-shared-screen directives for new scope | Claim v1.2 content; silently supersede v1.1; transplant unverified output contracts | Recovery OR signed exception identifying exact rules retained, superseded and replaced | Product Authority |
| SRC-EXC-002 | DOC-005 v1.1.0 | UNRECOVERED | Confirmed DOC-005 v1.0.2 for ten-agent logical semantics; new 19-engine design as separately labeled proposal | State DOC-005 v1.1 establishes platform services; assume 1:1 agent engine equivalence | Recovery OR signed compatibility/migration ADR and schema acceptance | Architecture Authority |
| SRC-EXC-003 | CCR-001 v1.1.0 | UNRECOVERED | Library DOC-007 v1.1 as *bounded candidate* for directly written rules; user directives independently establish product scope | Treat CCR as adopted change request or cite its missing text as normative | Recovery OR signed exception/decision record explicitly covering CCR references | Product + QA Authority |

## Two independent review routes

**Route A — Evidence recovered:** attach exact source URL/file, version, content hash where bytes available, reviewer, and mapping; mark `RECOVERED_PENDING_REVIEW`, then `VERIFIED` after review. Recalculate conflicts.

**Route B — Source not recoverable:** Product/Architecture Authorities sign precise exception version, scope, expiry/revisit trigger, fallback documents and risks. Status becomes `EXCEPTION_ACCEPTED` ONLY following their recorded approval. Mere adoption of a design PR does not imply source recovery.

## Functional boundaries until decision

1. Product scope from user-confirmed requirements can be specified and implemented in a new platform without pretending the missing legacy parents exist.
2. The **new** LookSpec/session/technical-plan schemas must be authored and approved independently in Phase 02; missing parent text cannot be used as execution authorization.
3. DOC-007 v1.1 qualitative ranking and DOC-018 v1.2 test overlays remain **candidate rebaseline imports**; each statement must be reviewed with source and test impact before claiming canonical precedence.
4. Preserve legacy Notion history unchanged, including contradictions and original version labels.

**Gate implication:** G-00 remains `BLOCKED_FOR_APPROVAL` until the exceptions (or sources) and ADR precedence are formally disposed. There is no time-based automatic waiver.
