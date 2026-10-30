> **Superseded for engineering design by [ADR-ENG-002](ADR_ENG_002_V2_ENGINE_CONTRACT_ARCHITECTURE_2026-10-30.md).** ADR-001 is retained as the documented discovery of semantic drift. ADR-ENG-002 establishes the v2 target role baseline. It does not provide independent security or specialist approval, and it does not alter the synthetic v1 runtime.

# ABC ADR-ENG-001 — Engine responsibility and versioning

**Date:** 2026-10-30. **State: PROPOSED, not approved.**

## Identified mismatch

Product vision target:
- ENG-04: recommendation intelligence and visual/evidence analysis
- ENG-05: decision intelligence and feasibility
- ENG-06: technical procedure planning, following a locked selected look

Current synthetic runtime `isolated_engine_service.py`:
- ENG-04: `SyntheticBeautyAnalysis` (four non-media attributes)
- ENG-05: `SyntheticKnowledgeEngine` (offline fixture)
- ENG-06: `SyntheticDecisionEngine` (bounded candidate selection)

Thus all three remain **IN_PROGRESS** and their ownership alignment is a critical blocking gate. The working internal protocol is `abc.internal.engine.synthetic.v1`, not a released product contract.

## Proposed migration, not an approved rename

| ID | Target | Reuse | Required new contract |
| --- | --- | --- | --- |
| ENG-04 | Recommendation | Source-bound analysis as a sub-capability | Vision/evidence input, candidate specification, provenance and ranking |
| ENG-05 | Decision | Knowledge retrieval and old synthetic candidate filters as sub-capabilities | Feasibility, unknowns, risk and explainable decision |
| ENG-06 | Technical Plan | Preserve old synthetic decision behind a legacy test-only adapter | Look lock, current condition, professional findings, feasibility, procedure, materials, checkpoints, stop conditions, aftercare and specialist validation |

Keep `contracts/v1` frozen. Introduce typed versioned **v2 ports**, contract compatibility tests, explicit migration and rollback, and independently verified callers. Avoid silently changing meanings of ENG identifiers.

## Product rules

The specialist and customer operate together on one display. AI Studio must preserve identity, region locking, references, accepted edits and visual uncertainty. A selected look does not prove real-world feasibility. No real treatment planning or release without qualified specialist SOP, consent and independent professional/security assessment.

## Acceptance

- [ ] Product architecture owner signs the target responsibility decision.
- [ ] All three v2 ports and error cases are reviewed.
- [ ] Old synthetic consumers remain isolated, with contract version routing.
- [ ] Integration, rollback, provenance and cross-tenant negative tests pass.
- [ ] Completion gates independently pass with real-world specialist validation.

**Current outcome: ADR proposed, mapping blocker open, no COMPLETE claim.**
