# WP-000-02 — Source Authority Resolution & ADR Review Pack

**Program:** ABC-MEP-01.1 / Phase 00. **State:** `REVIEW_PACKAGE_PREPARED`; **Gate-00:** `BLOCKED_FOR_FORMAL_APPROVAL`.  
**Repository:** `saleheebrahimi2029-hub/abc-platform`; target branch `docs/engineering-baseline-20261028`, PR #1; `main` and Notion MUST NOT be changed by this work package.

## Decision baseline

- **User-established product direction (binding for requirements drafting):** real independent salon platform; same-device shared specialist/client session; specialist runs and validates; AI Studio primary; phased coverage for all agreed beauty services; version-bounded technical plans; GitHub is the future engineering record.
- **Not yet ratified engineering mechanism:** deployment topology, concrete APIs, identity policies, service-specific QA thresholds, model/provider selection, legal controls, exact SOPs and named accountable reviewers.
- **Old GPT-only version:** remains an accurately labeled historical V1 contract, not automatically erased, edited or reinterpreted as deployed platform code.
- **Missing parent records:** DOC-001 v1.2.0, DOC-005 v1.1.0 and CCR-001 v1.1.0 are REFERENCED, not recovered. No source text is manufactured and no blanket sign-off is implied.

## WP-000-02 deliverables

1. [Source recovery and verification](SOURCE_RECOVERY_LOG.md) — searches, positive and negative evidence, limits.
2. [Source exception candidates](SOURCE_EXCEPTIONS.md) — individually scoped, unsigned decisions for three missing parent documents.
3. [Authority resolution](AUTHORITY_RESOLUTION.md) — issue-by-issue precedence, conflicting clauses, rule carry-forward, prohibition list.
4. [Legacy agent→engine crosswalk](LEGACY_AGENT_TO_ENGINE_MAP.md) — migration without inventing existing services.
5. [ADR review packet](ADR_REVIEW_PACKAGE.md) — alternatives, risks, trade-offs, conflicts and scope for 10 ADRs.
6. [Interface and governance invariants](INTERFACE_GOVERNANCE.md) — executable-contract prerequisites for Phase 02.
7. [Migration disposition CSV](MIGRATION_DISPOSITION.csv) — all 20 MIGs traced to owner, decision and closure evidence.
8. [Decision register CSV](DECISION_REGISTER.csv) — review statuses, authorities and signatures.
9. [Blocked actions CSV](BLOCKER_ACTION_REGISTER.csv) — specific pending blockers, proposed accountable roles and required evidence.
10. [QA evidence discipline](QA_EVIDENCE_REQUIREMENTS.md) — separation of authoring QA from build/release QA.
11. [Reviewer decision form](REVIEW_AND_SIGNOFF.md) — no invented approvals or named staff.
12. [Gate-00 reassessment](GATE_00_REASSESSMENT.md) — conditional and current verdict.
13. [`scripts/validate_wp00002.py`](../../../../scripts/validate_wp00002.py) + CI job — structural audit for this package (NOT runtime tests).

## Workflow

`WP-000-01 Audit → WP-000-02 Resolution Package → authority/source-exception review → WP-000-03 owner assignments/closure → Gate-00 formal decision → PR review/merge → Phase 01/02 contracts`.

**Safety rule:** statuses `PROPOSED` and `USER_DIRECTIVE_RECORDED` must never be silently relabeled `APPROVED`. The current work adds reviewable decisions and controls, not platform functionality.
