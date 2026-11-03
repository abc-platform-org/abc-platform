# ENG-06 isolated synthetic review — technical and governance evidence

Status: **CI candidate / no operational release**. This document records checks, not external approvals.

## Scope and boundaries
- ENG-06 is an isolated, disposable PostgreSQL synthetic-review worker.
- Manual CI seeding only; no automatic ENG-05 outbox dispatcher, no ENG-07 dispatch, no customer-facing decision.
- The permitted receipt is `ACKED_BLOCKED_REVIEW_ONLY`, containing `BLOCKED_PROFESSIONAL_SOURCE`.
- Production and hosted execution remain denied; source provenance, consent, worker identity, lease and replay controls must remain fail-closed.

## Verifiable technical evidence
- Last verified passing baseline: commit `52b4beaa10553aa08e6720a6dffd166e9773cc59`, foundation CI run `41642164693` and documentation integrity run `41642164866`, both successful.
- PostgreSQL negative-path tests added after that baseline: `runtime/phase04/tests/test_eng06_pg_isolation_negative.py`. They check FORCE RLS, dedicated-login denial of direct table reads, unbound claim denial, stale ACK/FAIL rejection and absence of orphan results.
- This added test must pass in a subsequent CI run before claiming its acceptance.
- Positive end-to-end Claim/Lease/ACK, concurrent claims, expiry/reclaim, retry/DLQ, consent revocation during processing, and ENG-14 handoff tests require independently recorded integration evidence before a technical gate is marked complete.

## External governance requirements (NOT APPROVED)
1. Independent credential issuer verification, current credential status and revocation evidence for every professional reviewer.
2. Version-bound source provenance, copyright/licensing and commercial-use permission reviewed by independent legal counsel.
3. Qualified specialist signoff on source applicability, conflicts, uncertainties and scope.
4. Recorded governance decision specifying authorized engine, tenant, jurisdiction, purpose, expiry, rollback and revocation procedure.
5. Independent security review of production service identities, mTLS/JWT, PostgreSQL authorization, ENG-14 and operational monitoring.

Until all evidence is independently authenticated, retain:
`eng05_ingestion_authorized=false`,
`eng06_dispatch_authorized=false`,
`customer_release_authorized=false`.

A successful CI run does **not** change those authorization decisions.

## Verification update
- Commit `8d2f3f7e493f1a72a5ee625635ed2efc881655d9`: foundation run `41643275468` **SUCCESS**; documentation run `41643275469` **SUCCESS**. Includes real PostgreSQL negative-path tests and deployed function contract assertions.
- Commit `bbbc51e19d86d693600e0e056aac95b955f845a9`: worker receipt regression added; CI status pending at time of this entry.
- These checks do **not** prove positive PostgreSQL ENG05 fixture → ENG06 Claim/Lease/ACK or concurrency, reclaim, replay and consent-revocation race. The technical acceptance gate stays **OPEN / NOT PASSED** until those execute with traceable logs.

## Verified synthetic PostgreSQL end-to-end acceptance (2026-11-03)
- Commit `d287f37fd769cda9faff20474dc7f6886f569511` passed **ABC Phase 04 local foundation CI** run `41647166653` and **Documentation integrity** run `41647166749`.
- New real PostgreSQL suite `runtime/phase04/tests/test_eng06_pg_positive_e2e.py` exercises manually seeded, synthetic-only ENG05 blocked artifact → independent ENG06 Claim → blocked decision → durable ACK, then denies replay. Additional cases cover expired lease reclaim and stale ACK fencing, concurrent claim exclusivity, and withdrawal of consent between Claim and ACK.
- This evidence demonstrates CI synthetic execution only. It does not verify actual independently authorized professional knowledge, managed production identities, or customer release. It does not imply approval to wire ENG05 outbox to ENG06 or ENG06 to ENG07.
- **Technical CI gate: PASS for isolated synthetic review scope only.** **External professional/legal/governance release gate: NOT APPROVED.** Preserve all authorization flags as false.

## Engineering continuation without external authority (2026-11-03)
- Decision: **CONTINUE_SYNTHETIC_ENGINEERING / DENY_OPERATIONAL_RELEASE**. See `governance/ENG06_PARALLEL_DEVELOPMENT_AND_DEFERRED_RELEASE.md`.
- External approvals are a tracked, non-waivable **release** dependency in GitHub Issue #79: https://github.com/saleheebrahimi2029-hub/abc-platform/issues/79 . They do not block fictional, local-only engine/contract/resilience engineering.
- Regression suite: `runtime/phase04/tests/test_eng06_deferred_release_policy.py` (hosted execution denied before DB I/O; unverified source yields zero candidates). CI evidence for this new suite must be verified separately.
- This decision does **not** authorize professional-source ingestion, customer-facing results, ENG-07 dispatch, or production deployment. All release flags remain false.
