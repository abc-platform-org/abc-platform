# ABC A1 — Architecture approval record (candidate)

Status: PENDING INDEPENDENT APPROVAL. This file is not an approval.

Scope: six v2-to-canonical adapters and the legacy ENG19 review transport namespace.

Decision proposed:
- Canonical ENG06 owns decision; ENG11 visual QA; ENG15 technical planning; ENG19 automation.
- Historical ENG19 review tables are infrastructure and remain unchanged.
- Migration 0031 introduces additive, RLS-protected, disabled bridge registry, legacy staging and canonical shadow records for all six adapters.
- No production principals receive grants; no canonical dispatch or customer release.
- Backfill and dual-read must preserve digest, scope, consent and policy provenance. Rollback must be demonstrated against disposable PostgreSQL.
- No professional source is promoted to trusted status by migration.

Review checklist:
1. Verify immutable CI SHA includes migration 0031 and A1 tests.
2. Inspect actual schema/role privileges and migration compatibility.
3. Validate security and specialist gates independently.
4. Approve or reject canonical ownership and ADR-ENG-003/004 in an attributable review.

Architecture owner: UNASSIGNED / NOT SIGNED
ADR-ENG-003 approval: PENDING
ADR-ENG-004 approval: PENDING
Customer release: DENIED
ENG07 operational dispatch: DENIED

A1 closure remains blocked until signed owner review and passing same-SHA CI.
