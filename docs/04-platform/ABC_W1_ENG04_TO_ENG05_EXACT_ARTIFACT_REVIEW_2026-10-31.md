# ABC W1 — ENG04 persisted analysis to authenticated ENG05 durable review (synthetic CI only)

**Engineering date:** 2026-10-31
**Status:** DRAFT / NO LIVE DISPATCH / NO INDEPENDENT SECURITY SIGNOFF
**Stack:** PR #65 independent ENG04 Worker → this PR; protected `main` untouched.

## Exact same-artifact execution contract

One disposable PostgreSQL16 test session processes **four actual synthetic consultation answers** through ENG02→ENG14→ENG03, which generates immutable, source-provenance evidence. A separate physical ENG04 database worker role ACKs a generated `BEAUTY_ANALYSIS_REPORT` into `abc.eng04_ci_results`. Only an ACKed report with exactly the same source bytes, SHA-256, source manifest, tenant, branch, consumer, session and state version can be admitted by the new `abc.eng19_submit_verified_eng04` SQL broker in migration **0024**.

The producer constructs the existing canonical review envelope and sends the *persisted* analysis JSON over a local TLS1.3 socket with mutually verified ephemeral certificates and a short-lived asymmetric JWT bound to the source ENG04 certificate and target `abc-engine:ENG-05` audience. The receiver independently checks JWT/peer, scope, consent and ENG14 policy doubles; Postgres atomically claims one-time JTI, rechecks real session/version/consent, verifies the recorded ENG04 result bytes and ENG03 source digest, then stores an immutable ENG05 Inbox record and source Job in one SQL transaction. An Inbox receipt **does not execute a professional knowledge model**, issue a customer recommendation or release ENG05→ENG06.

### Migration 0024 security properties

- Source verification is performed with the database-owned `eng04_ci_jobs`, `eng04_ci_results`, `eng04_ci_worker_bindings` and `eng03_evidence_ledger`. Untrusted envelope hashes, caller-supplied job IDs or a JWT alone cannot manufacture a valid source.
- It preserves the frozen historical tenant-test synthetic function, avoiding semantic changes to v1/v2 routes. The new broker is accessible only to the local `abc_app` gateway permission group, not to ENG04, ENG05 or legacy pipeline database roles.
- ENG05 receipt and source-job effects share one transaction and enforce exact immutable same-handoff idempotency. The receiving queue remains review-only, with professional source validation absent.
- Revoked consent and paused or stale session state prevent persistence through the existing DB-owned function. A tenant-foreign source cannot match the ACKed ENG04 result. The exact ENG03 source-manifest is rechecked.

## Test matrix

- Actual ENG02/ENG14/ENG03→independent ENG04 Claim/ACK→TLS1.3+JWT authenticated ENG05 receiver→durable Inbox/source-byte equality and no duplicate insertion.
- Same handoff ID, **new** valid one-time JWT is idempotent; replay of the *same* JWT is denied.
- Modified attribute, conflicting same-handoff message, wrong engine and wrong consumer JWT are denied.
- Independent policy denial and revoked consent deny the destination; no partial Inbox/Job is recorded.
- Simulated connection outage retries only with fresh one-time JWT; recovery persists one receipt.
- Pre-existing ENG04 physical role, stale lease and tampering tests remain active; 24 append-only migrations, checksum/DRIFT, FORCE RLS and nonroot CI must pass.

**Limits:** All certificates/keys and authorities in this path are disposable CI fixtures. The ENG04→ENG05 loopback transport is not a deployed internal private mesh; ENG05 queue creation does not authorize release, live salon use, actual image processing or ENG05→ENG06 operation. ADR-ENG-003/004 ratification, managed identities, private network and professional evidence qualification are separate unsatisfied requirements. All formal engine G01–G10 gates remain OPEN.

**Acceptance rule:** Only the exact final PR-head Foundation CI and Documentation Integrity results can establish *synthetic same-artifact review-path* engineering validation; independent authorization requires external evidence and reviewers.
