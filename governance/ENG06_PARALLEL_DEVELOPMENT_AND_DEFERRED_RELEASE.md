# ENG-06 — Parallel engineering / deferred professional authority policy

Decision: **CONTINUE_SYNTHETIC_ENGINEERING / DENY_OPERATIONAL_RELEASE** (2026-11-03).

Accountable external-dependency tracker: [GitHub Issue #79](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/79). Technical evidence: [ENG06 isolated acceptance](ENG06_ISOLATED_REVIEW_ACCEPTANCE_20261103.md).

## Two independent tracks

| Track | Current decision | Permitted work | Explicitly prohibited |
|---|---|---|---|
| A — Synthetic engineering | CONTINUE | Versioned contracts, state transitions, worker queues, PostgreSQL Claim/Lease/ACK, idempotency/replay, concurrency, consent revocation, synthetic visual/specification interfaces, QA and observability in disposable CI | Actual customer sessions, medical/cosmetic procedure instructions, real professional claims, real-source promotion, customer-visible recommendations |
| B — Professional and operational authorization | PENDING_EXTERNAL_EVIDENCE | Source registry and credential intake **without trusted ingestion**, independent verification, licensing/legal review, specialist approval, security assessment, rollout planning | Claiming approval without independent evidence, enabling real professional knowledge or release flags |

## Runtime invariants (non-negotiable)
1. `ABC_ENV=LOCAL_INTEGRATION_ONLY` is required by the synthetic ENG-06 review worker; only the disposable `abc_phase04_ci` database and `abc_eng06_ci_login` service login may be used by its executable entrypoint.
2. CI jobs are manually seeded, based on fictional fixtures, and never read the ENG-05 blocked outbox as an automatic production dispatcher.
3. ENG-06 review outputs are always `BLOCKED_PROFESSIONAL_SOURCE`, `downstream_dispatch_authorized=false`, `customer_release_approved=false`. The durable receipt is `ACKED_BLOCKED_REVIEW_ONLY`; it must never trigger ENG-07.
4. Missing, stale, contradictory, revoked or unverified professional authority is a **hard stop on operational behavior**, not a hard stop on non-operational engineering.
5. No CI success, completed mock UI, Issue closure, developer flag, or code merge is a substitute for independent authorization.

## Engineering continuation (does not depend on external sources)
- Implement engine-to-engine contract schemas, typed error envelopes, lineage hashes, deterministic replay and idempotency.
- Build ENG-06/07 interface adapters against synthetic fixtures only, with explicit `UNVERIFIED` evidence classification and disabled production dispatch.
- Expand resilience: crash recovery, stale leases, concurrency, retries/DLQ, audit, telemetry, consent-withdrawal races, tenant separation.
- Prepare source/credential/licensing intake interfaces and validation schemas, but never mark evidence verified without independent reviewers.
- Maintain separate CI synthetic acceptance and external release acceptance reports.

## Deferred release gate (tracked by Issue #79)
Independent source provenance; issuer-verified specialist credentials; rights and commercial-use clearance; professional safety/uncertainty validation; managed identity/mTLS/JWT and ENG-14 security signoff; signed scoped governance decision; explicit production release and rollback review.

**Release gate:** `eng05_ingestion_authorized=false`, `eng06_dispatch_authorized=false`, `customer_release_authorized=false` until all independently evidenced and explicitly approved. Any missing item keeps release blocked. This document is a development authorization **only**.
