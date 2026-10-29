# ABC-MEP-01.1 — Phase 04 platform foundation execution record

Date: 2026-10-29  
Branch: \`foundation/phase-04-runtime-20261029\`  
Base: \`main@1b479453c155b5744ec95e136733cce16a34ae88\` (Phase 00–02, **design-only accepted**)  
Issue: [#22](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/22)  
Engineering authority: delegated internal implementation decision; **no independent security/legal/privacy/SOP/product-release acceptance**.

## Original Phase-04 exit conditions

Canonical [ABC-MEP-01.1](../05-delivery/MASTER_ROADMAP_16_PHASES.md) requires deployable service skeleton, authenticated session API, image policy, base observability; demonstrate persisted/resumed sessions, unauthorized deny, job replay/idempotency. This PR is an **early vertical slice**, not full exit.

## Implemented vertical slice / scope

| Feature | Code | Current evidence state |
|---|---|---|
| Session create/read matching P02 operationIds | \`runtime/phase04/abc_foundation/http_api.py\` | LOCAL_TEST harness |
| Tenant/branch/assigned specialist isolation | \`auth.py\`, \`store.py\` | Synthetic token and negative tests; real IAM pending |
| Strict issuer/audience/expiry/HS256 | \`auth.py\` | Local-only; managed OIDC pending |
| Durable local state | SQLite WAL in \`store.py\` | Restart integration test |
| Pause/resume checkpoint | \`/_foundation/v0\` internal namespace | Exact-version CAS; \`CREATED\` only |
| Idempotent create and command replay | Database transaction + unique journal key | Identical key/payload replay; mismatch 409 |
| Atomic baseline event outbox | \`SESSION_CREATED\` canonical event | Consumer ACK and duplicate replay fixture |
| Fail-closed media, consent, service paths | HTTP 501 | Real provider integration is not present |
| Evidence and CI | Python unittest + GitHub workflow | Exact commit CI required |
| Base observability | Error/request IDs; no payload/secret logs | OpenTelemetry and deployed logs pending |

## Non-negotiable gaps for the actual Phase-04 closure

- External identity provider (OIDC/JWKS validation, MFA/step-up, key rotation, account disable/revocation) and server-side audited RBAC/ABAC for all roles and branches.
- Real privacy/consent system: client-origin proof, retention, deletion/DSR, legal jurisdiction, encryption and private object-store access; no images accepted today.
- Production-grade durable storage, migrations, encrypted backups/restore, DR and concurrency/load benchmarks. SQLite local dev is not a multi-node distributed datastore.
- Durable orchestrator beyond \`CREATED/PAUSED\`: all permitted state transitions, recovered visual jobs, async retries, queue workers, transactional outbox delivery, DLQ and idempotent consumers with full 25 event types; cross-service traces and incident metrics.
- API contract coverage for all other 39 operations, strict schema validation and contract-test integration; safe rate-limit/DoS controls and security/penetration test results.
- CI permissions, branch rules, dev/staging/prod infrastructure and complete observability; independent reviewers and a documented P04 exit decision.
- Real browser UX from Phase03 remains independently draft/blocked; no customer data, images, finance or chemical SOP is allowed in this test harness.

## Intentional security restrictions

1. The HTTP listener **refuses any host outside loopback**; no public API deployment.
2. Runtime **refuses to start unless \`ABC_ENV=LOCAL_INTEGRATION_ONLY\`**, a local SQLite file path and 32+ byte token signing secret are explicitly configured.
3. No external mint-token endpoint. Caller must supply signed, scoped token; bearer claims are validated before any protected data path.
4. No fake service packs, "consent given" endpoint or successful image uploads.
5. Product state \`PAUSED\` is a checkpointed internal proof; \`/_foundation/v0\` route is explicitly **not in frozen contract v1**. Schema changes require separate ADR and contract version.

## Phase decision

\`P04 = IN_PROGRESS\`  
\`WP-004-01 LOCAL_FOUNDATION = IMPLEMENTED_PENDING_EXACT_SHA_CI\` until checks are recorded.  
\`G06/G08/G09 = NOT_RUN\`; \`P03-UX-EXIT = BLOCKED\` independently.

The session/restore/replay/tenant test suite is prerequisite engineering evidence, not product-release authorization. No merge to \`main\` until review and gating.


## WP-004-01 implementation expansion — 2026-10-29

- **Local durable fixture job worker:** \`Store.enqueue_fixture_job / lease_fixture_job / finish_fixture_job / cancel_fixture_jobs\` with transactional SQLite lease ownership, forced stale-worker rejection, at-most-one live lease, three-failure dead-letter state and per-session cancellation. This proves **foundation queue semantics only**, not AI image processing or distributed queue production readiness.
- **Pause/race hardening:** a successful transition to PAUSED now invalidates queued/leased synthetic jobs **in the same transaction**, so late worker results cannot be acknowledged. Resume requires a fresh job intent and new idempotency key.
- **Contract inventory:** \`API_IMPLEMENTATION_MATRIX.csv\` maps all **41** frozen v1 operation IDs and routes to implementation status: exactly two \`LOCAL_HARNESS_ONLY\` and 39 \`NOT_IMPLEMENTED\`. None is released.
- **Additional executable tests:** 36 Python unittest cases including durable restart, tenant isolation, schema alignment, concurrent state-version compare-and-swap, idempotent replay, event envelope, lease crash recovery/expired-worker fencing and pause cancellation.
- **Automated traceability:** \`python scripts/validate_phase04.py\` fails if canonical operation IDs, route mapping, implementation status or release assertions drift. Runs in the Phase04 CI workflow.

**Boundary:** the local test-token issuer is *not* commercial identity infrastructure. \`G-06/G-08/G-09\` and formal Phase-04 exit are still NOT_PASSED. Do not accept real customers, photos, bookings, financial records or procedures. The documented 39 API operations and distributed orchestration/consent/privacy/production infrastructure backlog remain mandatory.


## Subsequent integrated implementation and revised gate — 2026-10-29

The point-in-time "managed OIDC and PostgreSQL still pending" statements above refer to the **earlier local SQLite slice**. The subsequent PR branch now implements **tested staging adapters**, not an actual connected managed provider:

- RSA-signed OIDC access-token verifier with configured/pinned HTTPS issuer, audience and JWKS; only issuer+subject enter the authorization pipeline. The JWT does not grant role/tenant access by its own claims.
- PostgreSQL 16 core migrations \`0001_postgres_core.sql\`, \`0002_checkpoint_audit.sql\`, dedicated non-BYPASSRLS \`abc_app\` role, FORCE RLS and server-verified active membership.
- PostgreSQL atomic session create/get, session checkpoint pause/resume with CAS and state audit, request idempotency and canonical outbox event.
- End-to-end HTTP → OIDC → PostgreSQL membership → RLS tests, including revocation. Legacy HS256 and SQLite remain explicitly local test harnesses.
- Read-only purpose/client/session-bound consent gate. Actual client attestation and withdrawal services are NOT implemented; no images, AI jobs or customer data can enter.
- Real temporary PostgreSQL CI database and 70 Python test scenarios, plus the frozen 41-operation traceability check.

**Current authoritative audit:** [IDENTITY_POSTGRES_CONSENT_AUDIT_2026-10-29.md](IDENTITY_POSTGRES_CONSENT_AUDIT_2026-10-29.md). Read this together with the historical baseline, not as a replacement for P02 contracts.

**Gate decision:** \`WP-004-01 = STAGING_ADAPTERS_IMPLEMENTED_PENDING_FINAL_HEAD_CHECK\` until exact-commit CI passes; \`P04 = IN_PROGRESS\`; external IdP/managed DB, independent consent verifier/DSR, distributed jobs, full 19 engines, observability, product deployment, human security and privacy approval remain OPEN. No merge to main or live usage authorized.
