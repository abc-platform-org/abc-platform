# Phase-02 Contract Test and Gate Evidence Plan

## Contract suite — executable *specification* validation
- `CT-SCHEMA-01`: all JSON schemas valid Draft-2020-12; refs resolve locally; valid fixtures accepted; invalid fixtures rejected.
- `CT-ID-01`: all 19 ENG IDs present, unique, explicit I/O schema refs, owner, auth and failure types.
- `CT-API-01`: OpenAPI 3.1 paths, auth, mutation idempotency and expected version guards present; all Schema refs resolve.
- `CT-EVENT-01`: declared event types in event registry covered by envelope and outbox rules.
- `CT-STATE-01`: each transition references registered source/target with guard and actor; no casual skip to `VALIDATED`.
- `CT-SEC-01`: no media side-effect without consent, no plan validation by client and no cross-tenant data trust.
- `CT-MAP-01`: original 64 Phase-01 IDs retained; engine source/consumer mapping has all ENG-01..19.

## Runtime suites deferred to subsequent phases
- `SES`: optimistic concurrency, crash recovery, async out-of-order.
- `PQ`: adaptive question decision impact/stop conditions, contradictory client answers.
- `VIS`: actual mask fidelity, identity preservation, reference isolation, multi-view quality, provider failures.
- `TEC`: qualified specialist validation and stale signoff, chemistry cannot invent SOP parameters.
- `SEC`: negative tenant/branch/privilege and consent lifecycle tests; penetration/privacy review as appropriate.
- `BUS`: real transaction reconciliation and action receipt.
- Original 120 Golden scenarios remain `AUTHORED_NOT_EXECUTED`; no 120/120 claim.

## Gate-02 formal acceptance
Requires full schema/API/state/event/owner coverage **and** human review of unresolved Gate-00 source/ADR issues, qualified safety/privacy consultation where applicable, and signed decision on exact artifact commit. A passing docs/JSON-Schema CI is `CONTRACTS_DRAFT_STRUCTURALLY_VALIDATED`, **not** `G02_FORMAL_PASS`.
