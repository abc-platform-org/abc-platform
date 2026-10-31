# ABC W1 — ENG-04 / ENG-05 Database Permission & Runtime Identity Separation

**Date:** 2026-10-31  
**Status:** CI IMPLEMENTATION CANDIDATE / NO LIVE DEPLOYMENT / NOT INDEPENDENTLY APPROVED  
**Base:** Draft PR #62, source-controlled candidate for the canonical 19-engine ABC architecture.

## Engineering decision and scope

The existing bounded ENG-05 professional-knowledge **review worker** used the older `abc_pipeline_worker` permission group. That group also represents the legacy combined ENG-04/05/06 synthetic pipeline, making independent revocation and least-privilege separation impossible at that boundary. This PR removes the common database permission group from the independent **ENG-05 review worker**, not from the still-frozen legacy synthetic pipeline. It never relabels legacy v1/v2 contract IDs or promises that the ENG-04 engine is operationally separated across every historical call path.

The canonical ownership remains ENG-04 Beauty/Visual Analysis, ENG-05 Professional Knowledge/Ontology, ENG-06 Decision; ENG-01 orchestrates and ENG-14 gates decisions. All old v1/v2 artifacts, historic migration files and the blocked ENG-05→06 outbox are preserved.

## Concrete implementation

1. Append-only migration `0022_eng04_eng05_permission_isolation.sql` creates independent `NOLOGIN NOINHERIT` groups `abc_eng04_worker` and `abc_eng05_worker`, plus a distinct, revocable, tenant/consumer scoped ENG-05 physical LOGIN binding table, with `ENABLE/FORCE ROW LEVEL SECURITY`.
2. The four existing ENG-05 review broker functions are recompiled under migration-owner `SECURITY DEFINER` with all identity and entitlement lookups scoped to `abc.eng05_worker_bindings`, instead of the common `abc.eng03_worker_bindings` and `abc.worker_login_bindings`.
3. EXECUTE privileges for Claim, ACK and FAIL are revoked from the old `abc_pipeline_worker` group (and ENG-04); only the new ENG-05 group receives narrowly scoped broker execution. No worker receives direct read/write access to ENG-05 jobs, results or outbox tables.
4. ENG-05 Python worker uses `SET LOCAL ROLE abc_eng05_worker` for each bounded transaction. Claims continue requiring the current tenant, consent, version and physical scoped login binding; ACK remains lease-fenced with revocation checks, with only a `BLOCKED_PENDING_AUTHORITY` outbox record.
5. Disposable PostgreSQL CI creates separate physical `abc_eng04_ci_login` and `abc_eng05_ci_login` accounts with `NOINHERIT`, grants each **only** its corresponding role and asserts no ENG-05 membership in the pipeline group.
6. The original migration scripts 0001–0021 remain immutable. Migration 0022 is included in the staging checksum manifest, tested for idempotent reruns and checksum drift.
7. Negative PostgreSQL tests require that an ENG-04 principal cannot `SET ROLE` as ENG-05 or call the ENG-05 Claim broker; ENG-05 cannot assume pipeline permissions, cannot query the restricted binding table and loses ability to ACK after either its scoped login binding is revoked or the client's consent becomes invalid.

## Remaining architectural and operational blockers

- The **legacy combined `SyntheticAnalysisPipeline`**, which still executes older ENG-04/05/06 synthetic logic behind `abc_pipeline_worker`, is preserved for backward compatibility. It must later be decomposed behind three engine-owned contracts, not silently renamed or promoted as an operationally independent ENG-04.
- `abc_eng04_worker` is a scoped, isolated **role skeleton**, not a completed independent ENG-04 analysis executor. The new CI physical login is synthetic, not an externally attested managed identity.
- The new `abc_eng05_worker` is an independently constrained *local review worker*. Both groups remain **unprovisioned on any verified private cloud environment**; this migration does not override W1's missing PKI, network, external managed PostgreSQL or operator approval.
- ENG-05 professional sources are unverified; ENG-06 must remain `BLOCKED_PROFESSIONAL_SOURCE`. All G01–G10 acceptance slots remain OPEN, and ENG-05→ENG-06 automatic delivery remains disabled.
- ADR-ENG-003 and ADR-ENG-004 remain proposed and unsigned. No customer media, real specialist treatments, paid provider API, automatic deployment or edits to protected main.

## Test/release gate

Run Foundation CI on the **exact final PR commit**: SQL bootstrap, 22 migration checksum and FORCE RLS validations, negative cross-engine permission tests, ENG-05 Claim/Lease/ACK/DLQ, ENG-06 blocked decision, 19-engine contract checks, W0/W1 governance tests, non-root container and no-public-start tests. Passing CI establishes only this scoped implementation candidate; live W1 remains gated by owner-approved private infrastructure and independent security/SRE evidence (Issues #58, #60, #63).

**Next bounded step:** extract ENG-04 from the legacy combined pipeline into an engine-owned durable analysis worker and explicit ENG-04→ENG-05 artifact transport; prove independent identities and negative tenant cross-access before promoting any v3 review edge. Preserve the existing synthetic combined path until signed migration/cutover evidence exists.
