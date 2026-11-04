# A2 ENG-02 — Test evidence mapping
Status: SOURCE_MAPPING_COMPLETE / CI_SAME_SHA_PENDING / OPERATIONAL_GATES_OPEN
Tracker: #81

## Source inventory
- `eng02_consultation.py`: deterministic synthetic-only SQLite consultation.
- `eng02_pg_outbox.py`: synthetic-only transactional PostgreSQL command/outbox path.
- `tests/test_eng02_consultation.py`: 13 named tests (question order, escalation, replay, tenant isolation, persistence, concurrency).
- `tests/test_eng02_precapture_http.py`: 6 named tests (consent/identity preflight, capture remains disabled).
- `tests/test_eng02_signed_pg.py`: 15 named tests (signed ingress, atomic event/receipt, parallel commands, revocation, scope and SQL role isolation).
- `tests/test_pg_outbox.py`: 16 named tests (delivery, lease/ACK, crash/retry, DLQ, isolation and reconciliation); shared transport evidence, not ENG-02 independent-service certification.

These are 50 named source tests, NOT 50 confirmed passing tests. Latest observed CI #491 was QUEUED at this checkpoint.

## Gate candidates and unresolved verification
| Gate | Evidence candidate | Missing proof | State |
|---|---|---|---|
| G01 | consultation + signed PG tests | Approved real-service consultation contract and CI evidence | OPEN |
| G02 | signed PG tests | Managed independent service identity | OPEN |
| G03 | signed PG + outbox tests | Deployed DB grants and tenant RLS | OPEN |
| G04 | signed HTTP socket test | Real deployed signed envelope chain | OPEN |
| G05 | consultation replay + signed PG parallel tests | Current-SHA CI acceptance | OPEN |
| G06 | PG outbox lease/ACK/DLQ tests | Independent operational consumer and recovery | OPEN |
| G07 | question escalation and safety halt tests | Full ENG14 runtime policy coverage | OPEN |
| G08 | precapture and revocation tests | Real-client consent lifecycle | OPEN |
| G09 | event receipts | Trace, metrics, p95/p99 and alerting | OPEN |
| G10 | all negative tests | Current-SHA CI, security and recovery signoff | OPEN |

## Engineering decision
ENG-02 remains PARTIAL. No real-client intake, real professional advice, independent deployment, or customer release is authorized. No A1 adapter status changed. The next stage is exact CI and migration-to-test trace verification, followed by ENG-03 audit.
