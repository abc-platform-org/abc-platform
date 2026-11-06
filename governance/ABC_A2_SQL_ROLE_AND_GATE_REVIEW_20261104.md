# ABC A2 — PostgreSQL role and security evidence review
Status: SQL_SOURCE_VERIFIED / CI_PENDING / RELEASE_BLOCKED
Tracker: #81

## SQL migrations directly inspected
| Migration | Verified source observations | Operational gap |
|---|---|---|
| 0012 ENG03 executor | abc_eng03_worker and abc_pipeline_worker grants; RLS ENABLE/FORCE on worker bindings; broker policies | Production credentials, isolation and restart drill |
| 0022 ENG04/ENG05 isolation | abc_eng04_worker and abc_eng05_worker identities; ENG05 worker bindings RLS ENABLE/FORCE and revocations | Managed identity issuance, deployed grants and security review |
| 0025 ENG05 verified provenance | ENG05 source receipts RLS ENABLE/FORCE; explicit revoke/grant of review claim/ACK functions | Independently accepted professional sources and production authority |
| 0021 ENG06 review worker | abc_eng06_review_worker role; RLS ENABLE/FORCE for review tables; function revocations | Only synthetic blocked professional result; no customer decision |
| 0011 ENG14 broker | Restricted privileged proof issue function and audit INSERT revocation | Complete transition policy coverage and independent approval |
| 0019 legacy review transport | Review inbox RLS ENABLE/FORCE, restricted review handoff function | Legacy ENG19 transport not canonical ENG19 automation |

Source review is not a live database permission test. Additional migrations and test coverage remain subject to full reconciliation.

## Evidence ledger controls
The eight-scope ledger now contains candidate module, migration-prefix and test paths. The A2 validator checks that each referenced file exists and each migration prefix uniquely resolves to one SQL file. A path passing this check is not proof that a test executed or that a security gate passed.

## Blocking conditions
1. Same-commit CI results must complete successfully; latest observed A2 runs were queued.
2. Link every G01–G10 gate to exact CI test, immutable SHA and reviewer before PASS.
3. Verify runtime role grants and RLS against a real isolated PostgreSQL instance.
4. Obtain independent managed-identity, network, resilience and professional approval where required.
5. Preserve all six A1 adapters disabled and ENG07 customer dispatch blocked.

Decision: A2 OPEN. No production-readiness, all-engine completion or professional authorization claim.
