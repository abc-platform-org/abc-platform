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
