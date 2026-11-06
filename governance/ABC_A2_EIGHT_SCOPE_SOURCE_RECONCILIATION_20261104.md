# A2 eight-scope source reconciliation — checkpoint
Status: SOURCE_INSPECTED / EVIDENCE_REVIEW_OPEN
Tracker: #81
This is a bounded source audit, not operational certification.

| Scope | Directly inspected code | Determination |
|---|---|---|
| ENG-01 | eng01_orchestrator.py, eng01_pg.py, eng01_service_identity.py, eng01_v2_authenticated_ingress.py | PARTIAL: guarded CREATED-to-PAUSED; no full canonical execution |
| ENG-02 | eng02_consultation.py, eng02_pg_outbox.py | PARTIAL: synthetic SQLite and PostgreSQL outbox only |
| ENG-03 | eng03_evidence.py, eng03_executor.py | PARTIAL: synthetic non-media evidence and PG claim/lease/fencing/ACK |
| ENG-04 | eng04_analysis.py, eng04_review_worker.py | PARTIAL: synthetic non-medical analysis and isolated worker; no image/model execution or live auto-dispatch |
| ENG-05 | eng05_knowledge.py, eng05_review_worker.py | PARTIAL: synthetic versioned knowledge, deny unverified sources, isolated PG worker; no approved professional corpus |
| ENG-06 | eng06_decision.py, eng06_review_worker.py | PARTIAL: offline synthetic hard filter and blocked professional-source receipt; no ENG07 dispatch |
| ENG-14 | eng14_policy.py, eng14_professional_gate.py | PARTIAL: synthetic question interceptor and conservative risk classifier; no qualified signoff or executable professional clearance |
| LEGACY_REVIEW_TRANSPORT | eng19_review_transport.py | PARTIAL: local-only TLS1.3 review-receipt socket; not canonical ENG-19 automation |

ENG-03 test mapping: `test_eng03_durable_pipeline.py` contains 28 named tests for durable pipeline, lease fencing, revocation, broker authority, DLQ, independent OS processes, ENG04/05 handoff, replay and network faults. `test_eng03_06_pipeline.py` contains 14 named tests for synthetic provenance and fail-closed decisions. These are source counts, not execution PASS.

## Gate disposition
G01–G10 remain OPEN across all eight scopes until exact immutable CI runs, test-to-contract evidence, independent reviewers and relevant deployment/operational proof are captured. Source presence alone cannot promote a gate to PASS.

## Release and architecture invariants
- A1 six adapters remain UNMIGRATED/DISABLED/QUARANTINED.
- No ENG06 professional advice or ENG07 live dispatch.
- Legacy eng19_review_* is transport, not canonical ENG-19 business automation.
- ENG06 legacy technical-plan code does not prove canonical ENG15 independent service.
- No production deployment or professional-source signoff is inferred.

## Next required evidence
1. Reconcile exact migrations, PostgreSQL roles and test cases for each scope.
2. Confirm same-SHA foundation CI result; do not equate queued jobs with success.
3. Populate G01–G10 with immutable test/CI references, reviewer and explicit remaining gaps.
4. Keep A2 OPEN until evidence ledger is fully reconciled.
