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
