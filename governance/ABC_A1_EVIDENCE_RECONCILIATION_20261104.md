# ABC A1 — Evidence reconciliation and closure gate
Date: 2026-11-04
Status: **OPEN / NOT APPROVED**
Scope: A1 canonical ownership, legacy reconciliation, adapters, reversible migration, and architecture approval.

## Provenance
- PR #78 branch: `implementation/w1-eng05-external-approval-gate-20261101`.
- GitHub Actions foundation run #465: **success**, run head `5eccf06218b6ada4954f15d586d5aa4bca2f5cde`; user-provided run log reports `Ran 614 tests in 145.947s / OK`. This is **not** evidence for later A1 commits.
- PR #78 head inspected before this evidence work: `7a45dbd168fe0b7ef049d9a0cec474e7414f39e6`.
- A1 PostgreSQL test correction: `809a6da054dda90f61c87923e0328363382674c3` (autocommit catalog probes; explicit transaction owns ON COMMIT DROP).

## Evidence inventory and limitations
| Gate | Evidence | Decision |
| --- | --- | --- |
| A1.1 ownership and legacy collision inventory | canonical 19-engine registry and legacy reconciliation JSON; static validators | REVIEW ONLY; owner ratification missing |
| A1.2 physical namespace inventory | `scripts/a1_inventory_physical_namespaces.py`, 30 ordered SQL migrations | STATIC ONLY; live catalog evidence not yet attached |
| A1.3 six versioned adapters | `governance/abc_v2_to_19_adapters.v0.review.json`; six entries all UNMIGRATED, runtime disabled | NOT IMPLEMENTED / NOT APPROVED |
| A1.4 negative quarantine | `scripts/a1_legacy_adapter_quarantine.py`, `runtime/phase04/tests/test_a1_legacy_contract_quarantine.py` | Code exists; latest-commit CI execution unverified |
| A1.5 migration, backfill and rollback | `runtime/phase04/tests/test_a1_physical_catalog_and_shadow_rollback.py` | Disposable temp-table simulation only; **not** real six-adapter reversible migration |
| A1.6 architecture owner signoff | adapter registry has `owner_signoff:false` | MISSING; cannot self-attest |

## Required acceptance evidence to close A1
1. Run current PR head in GitHub Actions with all A1 tests and collect run URL, exact commit SHA, pass/fail/skip counts.
2. Collect live disposable PostgreSQL catalog queries for actual schema, ownership, roles, RLS, grants, function security, migration history; compare to static inventory.
3. Implement and verify all six versioned adapters (including tenant, branch, session, provenance, consent, replay, conflict handling), with fail-closed dispatch.
4. Execute real versioned dual-read/backfill/rollback on disposable PostgreSQL; prove idempotency, reversibility, zero unauthorized customer dispatch, and absence of data loss.
5. Attach independent architecture-owner review/ADR and any mandatory security/specialist approvals with actual approver identity, timestamp and decision.
6. Only after all gates pass, change A1 from OPEN to CLOSED in the controlling plan. Do not infer production readiness or ENG07 authorization from CI success.

## Safety boundaries
No production migration, live release, external approval, or ENG07 customer dispatch is claimed or authorized by this report. The 614-test result applies to the older run SHA only.


## Final closure audit checkpoint — Run #475 (2026-11-04)

**Audit disposition: TECHNICAL CI VERIFIED / A1 CLOSURE BLOCKED.** This checkpoint supersedes earlier statements that same-SHA CI had not been observed; it does not supersede missing independent approvals or production restrictions.

### Immutable execution evidence
- Workflow: `phase04-foundation.yml`, run **#475**, https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/41824288543
- Exact run head: `ba2364df505f618d75e4abfa21051d9c61b3a28e`; branch `implementation/w1-eng05-external-approval-gate-20261101`.
- GitHub Actions result: **completed / success**; foundation job **success**, no failed steps.
- Explicitly successful steps: A1 six-adapter compatibility/quarantine contracts; A1 six-adapter PostgreSQL acceptance without skips; dedicated staging migrator against isolated ephemeral PostgreSQL.
- The workflow step title "A1 verify 30 migrations" is stale: staging migration manifest and CI acceptance now verify **31** migrations (0001–0031). Do not use the stale label as a count assertion.
- Staging migrator's `verify_staging_migration_ci.py` now asserts 31 migration receipts, checksum agreement, RLS/FORCE on the three A1 tables, and checksum-drift rejection.

### A1.1 — canonical ownership and legacy collision
**Technical source mapping present; independent decision NOT RATIFIED.** Canonical ENG-06 is decision/recommendation, ENG-15 technical planning, ENG-11 visual QA, ENG-19 opportunity automation. Historical `eng19_review_*` denotes review transport and is not canonical ENG-19. Registry is explicitly `PROPOSED_FOR_ARCHITECTURE_OWNER_REVIEW`, not an operational owner assignment.

### A1.2 — physical inventory
**STATIC + EPHEMERAL CI EVIDENCE; production/deployed catalog NOT VERIFIED.** `scripts/a1_inventory_physical_namespaces.py` inventories 31 SQL files and runtime references. The isolated staging CI validates migration receipts and table RLS. It does **not** independently establish the deployed production/staging catalog, all actual producer/consumer principals, network routing, or complete grants/functions against a real deployed environment. Preserve this distinction.

### A1.3 / A1.4 — six adapters and negative boundaries
**REVIEW-ONLY PROJECTION VERIFIED; operational migration NOT APPROVED.** Six adapter IDs are present in `0031_a1_six_adapter_bridge_quarantine.sql` and in the versioned review registry. Registry still records `UNMIGRATED`, `runtime_enabled=false`, `owner_signoff=false`. Migration enforces `enabled=false`, `dispatch_authorized=false`, `customer_release_approved=false`, FORCE RLS, PUBLIC REVOKE. CI proves test-only quarantine and negative contracts; it does not prove live canonical dispatch (which remains forbidden).

### A1.5 — migration/backfill/dual-read/rollback
**EPHEMERAL POSTGRESQL TEST VERIFIED; deployed cutover NOT EXECUTED.** `test_a1_six_adapter_pg_migration.py` verifies six synthetic source rows, idempotent `ON CONFLICT DO NOTHING` shadow copy, source/shadow digest and payload equality, release flags false, transaction rollback with no remaining synthetic rows, and no SELECT/INSERT privileges on shadow for three tested worker roles. `verify_staging_migration_ci.py` proves 31 migrations apply and reapply with checksums and drift detection. These are meaningful but bounded tests: no persistent live backfill, crash/restart recovery or actual production rollback, and no independently signed deployed catalog reconciliation. Do not conflate rollback of a test transaction with full operational schema downgrade.

### A1.6 — governance / independent approval
**BLOCKED.** `ABC_A1_ARCHITECTURE_APPROVAL_CANDIDATE.md` lists architecture owner UNASSIGNED/NOT SIGNED; ADR-ENG-003 and ADR-ENG-004 PENDING. No attributable independent architecture/security/specialist decision was found in the inspected A1 approval record. Owner authorization to execute engineering is not an independent signoff.

### Residual risks and next mandatory actions
1. Obtain attributable architecture-owner decision on the 19-engine mapping and the six historical collisions, plus ADR-ENG-003/004 decisions; retain reviewer identity, timestamp, scope, immutable SHA and rationale.
2. Obtain independent security review of RLS/GRANT/REVOKE, runtime identity and tenant isolation, policy/consent provenance, no-release controls and rollback; retain explicit approval or findings.
3. Reconcile the actual target environment's PostgreSQL catalog, privileges, identities, queue producer/consumer inventory and wire versions against the 31-migration inventory. If no approved environment is available, record this as BLOCKED rather than pretending an ephemeral test is deployed evidence.
4. If operational migration is in scope, separately prove a versioned deployed backfill, dual-read, replay/crash recovery and safe rollback under change control. No production cutover is authorized by this audit.
5. Once independent approvals and required environment evidence are attached, record an explicit A1 engineering closure decision; keep production/customer release and ENG-07 dispatch gated separately.

**Decision:** A1 remains **OPEN / EXTERNAL REVIEW AND DEPLOYED-EVIDENCE BLOCKED**. A2–A7 remain OPEN. No customer release, professional decision, ENG-07 operational handoff, or production migration is authorized.


## Deployment-scope clarification — owner statement, 2026-11-04
The project owner confirms ABC is currently **GitHub-only**, without a deployed application or persistent operational PostgreSQL environment. This is a scope statement, not a runtime observation or a security approval.

**A1 engineering-closure assessment shall be pre-deployment and evidence-gated:** require current immutable commit CI; disposable PostgreSQL migration catalog/roles/RLS/grants and six-adapter rollback/dual-read proof; documented static producer/consumer/identity/version inventory; explicit independent architecture/ADR-ENG-003/004 and security decisions. Do not demand production catalog evidence from an environment that does not exist, and do not represent disposable PostgreSQL as production.

**Deferred to deployment readiness:** real deployment catalog and service principal verification, network mTLS/JWT runtime attestation, production recovery/PITR, actual production rollback, customer load and release readiness. These must remain OPEN and explicitly block operational release, but are not automatically grounds to misstate the pre-deployment engineering tests as failed.

**Outstanding engineering gaps:** source inventory does not independently prove all producer/consumer/wire-version routes; current rollback test demonstrates transaction rollback, not full schema downgrade or crash/restart recovery; six adapters remain intentionally quarantined and unmigrated; independent architecture and security approvals are missing.

**Decision unchanged: A1 OPEN / PRE-DEPLOYMENT ENGINEERING CLOSURE PENDING.** No approval or closure is inferred from the owner's environment statement.


## Immutable CI acceptance — Run #477 (2026-11-04)
- Run: https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/41828511154
- Exact tested SHA: `7917cf6faf41dbf7d1d47a38b9a893aae48a1000`.
- GitHub reports `completed/success`; the single `foundation` job completed successfully.
- Explicitly successful steps include A1 six-adapter PostgreSQL acceptance without skips, staging migrator against isolated ephemeral PostgreSQL, integration/isolation/replay/persistence tests, canonical 19-owner inventory, adapter quarantine, PostgreSQL client certificate test, and nonroot container checks.
- The strengthened three-table CRUD privilege / FORCE RLS test is included in tested SHA via `ab1846120649e01a20a8174e84a883d8c7c07e16`.
- This supersedes the earlier 'new-head CI pending' notation. **Technical CI gate PASSED at SHA above**; this does not independently sign architecture or security, validate a deployed service, or close the source-route and full rollback evidence gaps.
- **A1 OPEN** pending attributable independent architecture, ADR-ENG-003/004, and security decisions, plus resolution/acceptance of remaining A1 source-route and rollback scope.
