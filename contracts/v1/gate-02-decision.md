# G-02 Decision — Phase-02 Contract Freeze

**State:** `DRAFT_CONTRACTS_FOR_REVIEW / G02_FORMAL_PASS_PENDING`.

## Required exit evidence
- [ ] ENG-01..19 typed input/output, owns one bounded responsibility and cannot self-approve cross-domain actions.
- [ ] JSON Schema Draft 2020-12 documents and fixtures valid; complete $ref resolution.
- [ ] OpenAPI 3.1 endpoints with role permissions, tenant derivation, state preconditions and idempotency defined.
- [ ] Events, outbox, idempotent job and failure rules specified, consistent with event type registry.
- [ ] No unsafe cross-state transition (client selection → technical authorization, failed visual QA → selected, no consent → image processing).
- [ ] Staleness/invalidation for selected Look, SOP/evidence/plan is explicit and reviewable.
- [ ] All 64 Phase-01 IDs linked to implementation responsibility and later test suites (Phase-01 matrices).
- [ ] Role/qualification, recovery, privacy and data lifecycle assumptions professionally reviewed where appropriate.
- [ ] Gate-00 prerequisite disposition approved or signed, scope-bounded exception; actual qualified reviewers named.
- [ ] Product/Architecture owner approves exact SHA, CI evidence and unresolved benchmark assumptions.

## Important boundaries
A contract can be machine-validated without being a deployed engine; real operations, API runtime and human specialist qualification are later phases. No fake unit test or visual QA claim. The 120 historic Golden tests remain authored but not run.
