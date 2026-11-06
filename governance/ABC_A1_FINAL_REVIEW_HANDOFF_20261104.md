# ABC A1 — Final engineering evidence and accountable review handoff
Date: 2026-11-04
Status: REVIEW REQUIRED / A1 OPEN
Scope: predeployment only; no customer release or operational routing.

## Verified CI evidence
- #479 success at 30304e933ae6bb21488facda38eaf1deec8a9cc3
- #480 success at aa04a61a56b7e6965b4af94a445ab31023d80fe0
- #481 success at 4598a2908b07980d98c3cd219442a6e663a92506
- #483 success at f90e5476b7999d820e7ee50ce68b8da53a9e3c55
- The current-head audit update must receive a new CI result. Prior successes do not attest later commits.
- #483 tests a real PostgreSQL container restart with committed synthetic records; it is NOT forced crash/PITR.

## Six adapter decision register
All six are conceptual source-to-destination mappings only, currently UNMIGRATED and disabled.
| Adapter | Source owner | Target owner | Executable producer/consumer proof | Decision |
|---|---|---|---|---|
| A04_TO_06_DECISION_INPUT | ENG04 recommendation | ENG06 | NOT VERIFIED | HOLD |
| A04_TO_07_LOOK_SPEC_INPUT | ENG04 recommendation | ENG07 | NOT VERIFIED | HOLD |
| A05_TO_06_DECISION_EVIDENCE | ENG05 decision | ENG06 | NOT VERIFIED | HOLD |
| A06_TO_15_PLAN_CANDIDATE | ENG06 technical planning | ENG15 | NOT VERIFIED | HOLD |
| A04_PIXEL_TO_11_QA_EVIDENCE | ENG04 historical embedded pixel QA | ENG11 | NOT VERIFIED | HOLD |
| A06_SOURCE_TO_16_REVIEW_EVIDENCE | ENG06 historical source signature | ENG16 | NOT VERIFIED | HOLD |

Source: governance/abc_v2_to_19_adapters.v0.review.json
Audit: scripts/a1_verify_adapter_runtime_bindings.py
Quarantine: migration 0031; no runtime role grants; FORCE RLS; release false.
No operational producer/consumer may be inferred from engine IDs, literal string references, or historical eng19_review transport.

## Architecture / security decision record (unsigned)
| Gate | Assigned decision coordinator | Independent reviewer | Decision | Evidence |
|---|---|---|---|---|
| Canonical 19-engine ownership and legacy collisions | saleheebrahimi2029-hub | NOT DESIGNATED | PENDING | — |
| ADR-ENG-003 | saleheebrahimi2029-hub | NOT DESIGNATED | PENDING | — |
| ADR-ENG-004 | saleheebrahimi2029-hub | NOT DESIGNATED | PENDING | — |
| RLS, principal isolation, migration safety | saleheebrahimi2029-hub | NOT DESIGNATED | PENDING | — |
| A1 predeployment closure | saleheebrahimi2029-hub | after gates | BLOCKED | — |

Reviewers must provide GitHub identity, exact SHA, date, findings, explicit APPROVE/REJECT and evidence links. Ownership assignment is not independent signoff. No approval is presumed or fabricated.

## Remaining closure actions
1. Obtain independently reviewed executable callsite/table/queue/principal/wire-version mapping, or explicitly ratify a narrowly scoped predeployment A1 in which all six adapters are permanently quarantined and unmigrated. Neither route authorizes customer dispatch.
2. Record architecture and security reviewer decisions with traceable evidence on PR #78 / Issue #80.
3. Capture current-head CI and update closure packet with the immutable run URL.
4. Decide whether server crash/PITR is an A1 predeployment gate or a separate deployment gate, with accountable documented risk acceptance. CI restart is not crash evidence.
5. Close A1 only after approved gate decisions. Do not automatically infer approval from green CI.
