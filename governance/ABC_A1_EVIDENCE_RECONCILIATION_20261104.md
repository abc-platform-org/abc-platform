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
