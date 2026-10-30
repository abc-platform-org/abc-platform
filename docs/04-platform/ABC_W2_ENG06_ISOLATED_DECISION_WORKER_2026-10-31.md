# ABC W2 — ENG-06 isolated decision-worker validation (synthetic CI only)

**Date:** 2026-10-31
**Decision:** REVIEW-ONLY ENGINE IMPLEMENTATION CANDIDATE; NO DEPLOYMENT OR RELEASE.
**Branch:** `implementation/w2-eng06-isolated-review-worker-20261031`, stacked after PR #59.
**Canonical role:** ENG-05 Professional Knowledge → ENG-06 Decision → ENG-07 Look Specification, under ENG-01 orchestration and ENG-14 policy governance.

## 1. What is actually implemented

- New PostgreSQL migration `0021_eng06_synthetic_review_worker.sql` creates dedicated, `NOLOGIN` permission role `abc_eng06_review_worker`, a revocable scoped identity binding, durable queue, and immutable result table. Each table has FORCE RLS and no application/worker direct-DML grant.
- CI bootstrap provisions a *different* disposable physical LOGIN `abc_eng06_ci_login LOGIN NOINHERIT` and grants only that role's permission group. It is not a hosted identity or a managed security issuer.
- Three SQL broker functions `eng06_ci_claim`, `eng06_ci_ack`, and `eng06_ci_fail` enforce exact physical session login/tenant/consumer, bounded leases, stale ACK protection, retry and DLQ. Jobs are claimable only while live, matching session state and non-revoked AI_PROCESSING+INTERNAL_HANDOFF consent are observed.
- Source lineage is joined to the preceding *ACKED* ENG05 job, validated ENG05 result digest and immutable ENG05 outbox record. The outbox remains `BLOCKED_PENDING_AUTHORITY`. `ENG06` cannot infer a professional source from unverified synthetic knowledge.
- The independent Python worker runs the bounded deterministic `SyntheticDecisionEngine` on its own claim, cross-validates ENG04/ENG05 artifact hashes, and records only `BLOCKED_PROFESSIONAL_SOURCE`. It is *not* allowed to create ENG07 look specifications, treat clients, perform technical planning or suggest an approved service.
- **No production enqueue capability** exists: only an ephemeral CI database administrator explicitly inserts synthetic jobs from a previously ACKED ENG05 result. This is a disconnected *test bridge*, not the operational ENG05→06 dispatcher.

## 2. Security and failure model

| Guard | Required behavior |
|---|---|
| Independent identity | Physical LOGIN distinct from ENG05; role group NOLOGIN; revocation fences ACK |
| Tenant/consumer scope | All claims and receipts restricted to active physical login binding |
| Source integrity | ENG04 analysis and ENG05 knowledge SHA256 checked against durable upstream bytes |
| Consent and state | Exact session/branch/state version, LIVE consent checked at claim and ACK |
| Lease/idempotency | One concurrent lease, stale lease denied, one durable result, bounded attempts |
| Unverified source | No actionable candidates; provenance reason `UNVERIFIED_KNOWLEDGE_SOURCE` |
| Recovery | Controlled failure requeue and terminal DLQ after three attempts |
| Data boundary | No real client photo, paid API, model/provider secret, media upload or remote mode |
| Network | Existing ENG05→06 local TLS review receipt is a separate proof; this Worker is not connected to that listener |
| Runtime | `ABC_ENV=LOCAL_INTEGRATION_ONLY` guard and no worker deployment |
| Release | No ENG05 outbox release, no ENG07 dispatch, customer release remains BLOCKED |

## 3. Test evidence / acceptance rule

The new tests validate process_once, immutable decision envelope, parallel lease competition, expired lease reacquisition, stale ACK denial, consent revocation at ACK, physical LOGIN revocation at ACK, direct DML rejection and three-attempt DLQ. The existing 19-engine architecture and W0/W1/W2 fail-closed gates remain mandatory.

Passing GitHub Actions means **bounded synthetic CI acceptance**, not independently authorized ENGINE COMPLETE. ENG06's G01–G10 quality gates remain open until professional domain quality, independent security/SRE review, actual managed identities and real private deployment are validated.

## 4. Next dependency after this PR

1. Exact-head CI must pass migration 0021, new tests and regressions before any merge proposal.
2. Independent ratification of ADR-ENG-003/004 and evidence from issues #58 and #60.
3. Managed private networking/identity/PG staging (no public engine endpoints), audit, restoration and rollback validation.
4. Build separately authorized ENG05 outbox dispatcher and proper authenticated ENG06 durable consumer that validates policy proof and signed provenance and only releases with a new explicit operational decision.
5. Separate specialist approved knowledge base, professional evaluation set, fail-safes and release controls before upgrading ENG06 to a service-grade recommendation engine.

**No changes to protected main, Notion or frozen v1/v2 contracts.**
