# ABC A1 — Six-adapter source/target reconciliation and evidence gaps
**Status:** SOURCE-MAPPED / NOT DEPLOYED / NOT INDEPENDENTLY RATIFIED
**Date:** 2026-11-04
**Scope:** `abc_v2_to_19_adapters.v0.review.json`, `abc_legacy_namespace_reconciliation.v1.json`, migration 0031.

| Adapter | Historical producer role | Canonical destination | Source protocol | Target protocol | Runtime consumer identity | Live route |
|---|---|---|---|---|---|---|
| A04_TO_06_DECISION_INPUT | ENG-04 recommendation | ENG-06 | abc.internal.engine.v2.draft | abc.internal.capability.v3.review | NOT VERIFIED | DISABLED |
| A04_TO_07_LOOK_SPEC_INPUT | ENG-04 recommendation | ENG-07 | abc.internal.engine.v2.draft | abc.internal.capability.v3.review | NOT VERIFIED | DISABLED |
| A05_TO_06_DECISION_EVIDENCE | ENG-05 decision | ENG-06 | abc.internal.engine.v2.draft | abc.internal.capability.v3.review | NOT VERIFIED | DISABLED |
| A06_TO_15_PLAN_CANDIDATE | ENG-06 technical plan | ENG-15 | abc.internal.engine.v2.draft | abc.internal.capability.v3.review | NOT VERIFIED | DISABLED |
| A04_PIXEL_TO_11_QA_EVIDENCE | ENG-04 embedded pixel QA | ENG-11 | abc.internal.engine.v2.draft | abc.internal.capability.v3.review | NOT VERIFIED | DISABLED |
| A06_SOURCE_TO_16_REVIEW_EVIDENCE | ENG-06 professional-source signature | ENG-16 | abc.internal.engine.v2.draft | abc.internal.capability.v3.review | NOT VERIFIED | DISABLED |

**Physical source-of-truth:** migration `0031_a1_six_adapter_bridge_quarantine.sql` declares `abc.a1_bridge_registry`, `abc.a1_bridge_legacy`, `abc.a1_bridge_shadow`, strict v2/v3 checks, forced RLS, and no runtime grants. These are *review-only shadow objects*, not six live queues or proof of runtime producer/consumer connections.

**Collision:** historical `eng19_review_producer.py`, `eng19_review_consumer.py` and `eng19_review_transport.py` are legacy review transport, **not** canonical ENG-19 opportunity automation. Historical ENG-06 CI tables and `eng19_synthetic_outbox` are likewise not proof of production ENG-07 routing.

## Required follow-up evidence
1. For each adapter, enumerate concrete originating table/queue and source write function, receiving table/queue and consumer callsite, principal, and exact wire schema; record explicit `UNKNOWN` when no executable binding exists. The six conceptual mappings above do not establish these facts.
2. Verify against a disposable PostgreSQL catalog (31 migrations) and source code references. Deployed catalog is deferred because no deployment exists.
3. Execute latest PostgreSQL tests at immutable SHA, including connection-loss transaction rollback and quarantine check constraints.
4. Prove restart-after-committed-write and crash/restart idempotency; provide a separate versioned **schema downgrade** plan and test. Existing transaction rollback is not schema downgrade.
5. Obtain attributable architecture, ADR-ENG-003/004 and security decisions. Assignment to owner is not independent approval.

**Decision:** A1 OPEN. Six adapters remain `UNMIGRATED`, `runtime_enabled=false`, `live_dispatch_enabled=false`, `owner_signoff=false`. No customer/professional release or ENG-07 dispatch.
