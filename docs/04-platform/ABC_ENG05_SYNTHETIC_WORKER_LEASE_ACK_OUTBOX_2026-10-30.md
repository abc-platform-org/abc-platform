# ENG05 — Independent bounded Worker, Lease Fencing and Transactional Outbox

**Date:** 2026-10-30. **Status:** CI-only synthetic execution; Draft PR #56. **Release:** BLOCKED.

## Implemented, without changing the frozen v1/v2 ABI

PostgreSQL migration 0020 adds three forced-RLS tables with no direct DML for the application or worker roles: `eng19_synthetic_jobs`, `eng19_synthetic_results` and `eng19_synthetic_outbox`. The existing authenticated ENG04→ENG05 mTLS inlet optionally carries one small canonical synthetic source artifact. In one DB transaction, the DEFNER validates the source bytes against the exact declared SHA256, scope and synthetic engine version; rechecks session/active purpose-specific consent; saves immutable inbox receipt and creates an idempotent job.

**Physical worker:** separately authenticated, existing `abc_pipeline_worker` role, not the API role `abc_app`. Tenant binding to this role's active subscription is mandatory. **This is not a new ENG05-specific managed service identity**; production requires a dedicated managed identity per engine and external CA/JWKS.

Worker Claim chooses one consent-current, session-version-current ready job via `FOR UPDATE SKIP LOCKED`, increments attempts, and issues a UUID Lease with 1–120-second TTL. Worker `process_once` rechecks source SHA256, session and synthetic data tags, runs the actual bounded `SyntheticKnowledgeEngine.resolve(...,fixture=None)` and refuses to fabricate a professional knowledge source. Durable ACK requires current Lease token, non-expired TTL, active workload binding, active non-revoked purpose consent and unchanged session state/version; result bytes + result SHA256 + ENG05 engine version, job ACK and ENG05→ENG06 outbox row commit together.

**Important:** The destination Outbox status is literally `BLOCKED_PENDING_AUTHORITY`, with a database CHECK disallowing any other value. This is an auditable, durable prepared handoff, **not an outbound network send or ENG06 job execution**. A future independently reviewed transport must prove exact audience, per-engine service identity, signed source evidence, policy ENG14 and specialist signoff before releasing the outbox. The full 19-engine workflow remains unbuilt.

Retry behavior: a stale lease token cannot ACK or fail; a crashed worker may be reclaimed with a *new* Lease until three attempts. Explicit bounded failure requeues (backoff) or DLQs at attempt 3; a third crashed lease eventually becomes DLQ. ACK and outbox are transactional. Unexpected source/claim or SQL errors fail closed. Consent withdrawal or a session version advance between Claim and ACK prohibits result and outbox insertion. No client media, real credentials or billable LLM APIs are used.

## Scope and limits

- New migration is journaled as 0020 in the offline staging migrator and CI. All three tables use ENABLE+FORCE RLS; an application/worker cannot directly query or mutate them.
- Synthetic-only tenant and branch are hard-pinned for this bounded proof. The previous 19-engine review-only receipt remains available without source attachment and without job creation.
- Actual specialist SOP and Beauty Knowledge VQ criteria, ENG05 production worker identity and real ENG06 outbound delivery are **not** accomplished by this code.
- ADR-ENG-003 and ADR-ENG-004 independently signed acceptance is required. All 190 G01–G10 gate slots remain OPEN, Phase04 IN_PROGRESS and customer release BLOCKED. No draft PR is merged, and protected `main` is untouched.

## Evidence

`test_eng19_actual_mtls_handoff_pg.py` adds integration tests using ephemeral real PostgreSQL16, two TLS1.3 listener network ports and an independent `abc_pipeline_worker` login. Cases include multi-worker SKIP LOCKED, stale lease fencing and recovery, real bounded ENG05 execution, result/outbox atomicity, consent cancellation between claim/ACK, retry/DLQ, direct SQL privilege denial and malformed source refusal.

`scripts/validate_eng05_review_worker.py` statically blocks an accidental refactor that drops the mandatory denial gates. Exact-head CI must pass independently before this branch is accepted even as an experimental baseline.
