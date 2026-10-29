# ABC Phase 04 — Durable events, tenant isolation and independent service execution

Date: 2026-10-29  
Branch: \`foundation/phase-04-runtime-20261029\` · PR #23 (draft) · Issue #22  
Authority: engineering integration only, **not** formal Phase-04 acceptance or production release.

## Implemented event-consumer vertical slice

\`\`\`text
OIDC RS256 identity → server-controlled membership/RLS → PostgreSQL session
   └── SAME TRANSACTION: canonical SESSION_CREATED outbox envelope
        └── worker role abc_worker (not HTTP abc_app)
             └── administrator-provisioned subscription: consumer ↔ exact tenant
                  └── reconcile missed events; unique consumer_id+event_id
                       └── SKIP LOCKED + bounded lease token/expiry/attempts
                            └── session-index service (independent process/no public port)
                                 └── unique idempotent, non-PII projection insert
                                      └── ACK after durable effect; otherwise retry/DLQ
\`\`\`

**Exact database boundaries:** migrations 0001–0006 applied by a separate privileged migration identity in disposable PostgreSQL 16 CI. The server uses \`abc_app\`; the worker uses \`abc_worker\`. Both roles have NO SUPERUSER/BYPASSRLS/CREATEROLE. The worker cannot read sessions, consent, membership or financial records; the HTTP role cannot select outbox or delivery ledger. No user, model or frontend can freely register subscriptions: \`abc.worker_subscriptions\` is admin-provisioned, ties each consumer to exactly one tenant and one allowed event type, enforced again by foreign key and RLS.

**Producer:** only \`SESSION_CREATED\` is emitted by the implemented server foundation, conforming to frozen P02 event envelope. Session create, outbox append and idempotency receipt are committed atomically. No success event for a fake model or consent is emitted.

**Transport:** \`abc_foundation.pg_outbox.OutboxDispatcher\` records consumer-specific deliveries. \`register()\` is idempotent and reconciles late events after worker restart. \`lease()\` uses \`FOR UPDATE SKIP LOCKED\` and unique tokens; concurrent workers cannot process the same lease. Successful processing is recorded via \`complete(... succeeded=True)\` only after the read-model effect is durable. Failed processing has backoff and becomes \`DLQ\` after 3 attempts; there is no uncontrolled automatic dead-letter replay.

**Independent executable consumer:** \`abc_foundation.session_index_consumer.SessionIndexConsumer\` validates event type, schema version, IDs, aggregate version, tenant and branch; it only writes a non-personal \`session_index_projection\` with a unique consumer/event key. Restart after "effect committed, ACK lost" replays the event but does not duplicate the projection. \`abc_foundation.service_session_index\` is an isolated, separately supervised worker entrypoint with **no inbound HTTP port** and explicit integration-only environment guard. Production workload identity, service discovery, metrics and deployment are still missing.

## Security regression discovered and fixed during tests

The first dispatcher implementation subscribed a consumer to **all** tenant events; initial cross-tenant tests failed because older events were leased. This was a genuine information-isolation defect, **not** a flaky test. Migration \`0004_tenant_subscriptions.sql\`, consumer scope checks, FK and regression tests make a subscriber unable to reconcile another tenant's event. Consumer deactivation blocks new leases and future ACK. See exact GitHub CI for proof.

## Consent safety and lifecycle

\`0005_consent_lifecycle.sql\` adds bounded \`valid_until\`, immutable original client/session/purpose/evidence, explicit \`PENDING_VERIFICATION → ACTIVE → WITHDRAWN/EXPIRED\` transitions, prohibition on reactivating terminal consent and a separate status audit. The read guard denies after validity expiry, on wrong purpose/client/session/tenant, for PENDING, after withdrawal or without independent verification.

**Important exception:** tests simulate an external verifier via CI **database administrator**, not by an actual client signature or connected legal consent service. The normal application account cannot write/approve/withdraw consent. Public image capture/storage and consent endpoints remain disabled. A real service will need customer-origin evidence, verification of disclosure version, identity/accessibility and lawful legal/privacy review before any LIVE use. No real deletion/DSR or object-store integration is claimed.

## CI evidence and exact status

At prior exact SHA the Python suite reached **88 passing tests**, including real PostgreSQL tenant isolation, independent role permissions, RSA OIDC HTTP E2E, per-consumer leasing, expired/stale token denial, crash reprocessing, consumer revocation, consent non-resurrection, and projection dedupe. Re-evaluate at the final PR SHA after every code/doc change. Documentation integrity and Python CI are separate check suites.

**NOT delivered in this vertical slice:** managed OIDC provider or actual user registration; tenant provisioning/identity admin UI; cloud database backup/restore; secure object storage/photo processing; externally witnessed consent; all 19 independent engine implementations; visual jobs/visual QA; entire 25-event graph; live salon business transactions; multi-region data residency; qualified pentest/privacy certification or public deployment.

## Remaining P04 production gates (must be evidenced, cannot be waived by passing synthetic CI)

1. Deploy real isolated dev/staging environment, external IdP configuration (issuer/JWKS), MFA/PKCE, key and session revocation, audited account provisioning, service workload identities.
2. Managed PostgreSQL, explicit migration ownership and rollback drills, TLS and connection secret rotation, encrypted backup/restore, PITR, tested RLS and cross-tenant penetration scenarios, monitoring and capacity measurements.
3. Dedicated verified-client consent capture/attestation, immutable proof, policy basis, withdrawal/DSR and retention deletion across DB and future objects; legal, privacy and specialist review.
4. Production event runtime: 25 typed events, durable failure/compensation semantics, backpressure/metrics, per-tenant worker identity (shared CI worker role is not production tenant isolation), DLQ review/redrive authorization, reliable bus and trace correlation.
5. Physical UX acceptance from Phase 03, image safety/visual benchmark gates, audited professional SOP evidence, and incident/runbook approvals before accepting actual photos or service execution.

**Formal decision:** \`P04 = IN_PROGRESS\` and \`G06/G08/G09 = NOT_RUN\`. Passing the outbox tests does **not** mean 19 engines or a production cloud system are running.
