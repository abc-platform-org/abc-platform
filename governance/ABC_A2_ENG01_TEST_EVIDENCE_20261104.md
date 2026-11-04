# A2 ENG-01 — Test evidence mapping (source-verified)
Status: SOURCE_MAPPING_COMPLETE / CI_CURRENT_SHA_PENDING / OPERATIONAL_GATES_OPEN
Tracker: https://github.com/saleheebrahimi2029-hub/abc-platform/issues/81

## Test files inspected
- `runtime/phase04/tests/test_eng01.py`: 19 named tests including state graph, forbidden transition, replay, stale version, real PostgreSQL receipt/audit, concurrency and tenant/revocation denial.
- `runtime/phase04/tests/test_eng01_pg_command.py`: 8 named tests for atomic receipts, metadata mutation, concurrent single commit, stale key, revoked membership, worker read denial and RLS.
- `runtime/phase04/tests/test_eng01_gateway.py`: 12 named tests for typed gateway command validation, principal, scope, idempotency and forged policy token.
- `runtime/phase04/tests/test_eng_service_identity.py`: 6 named tests for service JWT verification, issuer/audience, signature forgery and algorithm downgrade.
- `runtime/phase04/tests/test_v2_authenticated_ingress.py`: 8 named tests for local-only ingress, scoped authority, certificate, replay and blocked staging dispatch.

Counts refer to named source test methods, not a new test run. Current A2 CI #488 and #489 were QUEUED at inspection; no new PASS is asserted.

## G01–G10 mapping
| Gate | Source evidence candidate | Remaining gap | Decision |
|---|---|---|---|
| G01 | test_eng01.py; test_eng01_gateway.py | Exact same-SHA run and contract review | OPEN |
| G02 | test_eng_service_identity.py | Managed workload PKI and independent deployment | OPEN |
| G03 | test_eng01_pg_command.py | Deployment grants and tenant RLS verification | OPEN |
| G04 | test_v2_authenticated_ingress.py | Real network envelope/certificate proof | OPEN |
| G05 | test_eng01_pg_command.py; test_v2_authenticated_ingress.py | Same-SHA CI and distributed replay acceptance | OPEN |
| G06 | test_eng01.py; test_eng01_pg_command.py | Full durable workflow, lease/ACK/DLQ applicability and crash recovery | OPEN |
| G07 | test_eng01_gateway.py | ENG14 coverage across all canonical transitions | OPEN |
| G08 | test_eng01.py; test_eng01_pg_command.py | End-to-end consent withdrawal coverage | OPEN |
| G09 | test_eng01.py | Trace/metrics, p95/p99 and alerts | OPEN |
| G10 | all above | Same-SHA CI, independent review, recovery and threat evidence | OPEN |

## Conclusion
ENG-01 has bounded implemented source and test coverage; canonical 17-stage workflow and production independence remain unverified. No gate is promoted to PASS merely by listing tests. A1 quarantine remains intact. ENG-02 audit may begin without changing ENG-01 status.
