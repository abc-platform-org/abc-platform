# ABC Phase 04 — Local foundation runtime slice

**Status:** ENGINEERING_IN_PROGRESS / LOCAL_INTEGRATION_ONLY. This is not a deployed product, 19 working AI engines, or authorization for salon/client data.

## What is executable

- \`POST /v1/consultations\` — strict, scoped, idempotent session creation, canonical \`session.schema.json\` projection.
- \`GET /v1/consultations/{session_id}\` — tenant, branch and assigned-specialist protected read.
- \`POST /_foundation/v0/consultations/{session_id}/pause\`, \`/resume\` — **internal, versioned local-only POC routes**, not part of frozen v1 OpenAPI. Persist \`CREATED → PAUSED → CREATED\` checkpoints; expected-version CAS and replay.
- SQLite WAL local store; atomic session, idempotency ledger, audit, \`SESSION_CREATED\` event outbox. Local consumer ACK dedupe fixture is not a production distributed worker.
- Explicitly unavailable: client consent acceptance, image upload, analysis, visual jobs, specialist/chemical approval, financial transactions, service packs and remote API authentication.

**Authentication boundary:** HS256 test tokens validated strictly on a **loopback-only listener**. There is no token issuance endpoint. Claims have expiry, issuer, audience, tenant, branch, specialist; inbound tenant scope never comes from a request body. This verifier is deliberately **not** a production identity provider: real integration requires external OIDC/JWKS, key rotation, revocation, service-to-service policy and security review.

## Run locally (synthetic data only)

Python 3.12+; no third-party packages required.

\`\`\`bash
cd runtime/phase04
export ABC_ENV=LOCAL_INTEGRATION_ONLY
export ABC_DB_PATH=/tmp/abc-foundation-local.sqlite
export ABC_LOCAL_TEST_SECRET='<replace-with-locally-generated-random-32+byte-secret>'
python -m abc_foundation.server
\`\`\`

Binds \`127.0.0.1:8766\`. Non-loopback binding is intentionally refused. Do not publish, forward, expose to internet or feed real client or employee records. Use \`abc_foundation.auth.mint_test_token\` **only inside local automated tests**; it is intentionally not a public route or a user login mechanism.

Test:

\`\`\`bash
cd runtime/phase04
python -m unittest discover -s tests -v
\`\`\`

## Dependencies, authority and phase boundaries

- Branch \`foundation/phase-04-runtime-20261029\` starts from P00–P02 accepted design baseline on \`main@1b479453c155b5744ec95e136733cce16a34ae88\`. It **does not** merge or modify draft Phase-03 PR #21.
- This slice implements a minimal foundation for \`ENG-01\` state persistence; it does not claim 19 independent engines or a complete workflow engine.
- Independent formal Phase-03 accessibility and UX acceptance, real identity/consent/privacy/SOP/security experts and real deployment are still gate blockers.
- Proposed \`CR-03-001\` selected-look change after specialist selection is **not adopted** into frozen v1; do not add that transition to this runtime without a separate compatible contract version.
- Detailed exit matrix and unresolved controls: [PHASE04_EXECUTION.md](../../docs/04-platform/PHASE04_EXECUTION.md).


## Durable fixture job proof (not image processing)

The local store additionally exercises \`NO_MEDIA_TEST_FIXTURE\` jobs with durable queue state, atomic leases, bounded retry, dead-letter and stale-worker rejection. These methods have **no HTTP exposure**, no actual model calls and never accept image bytes. Pausing a session fences outstanding fixture jobs atomically. Tests prove crash/restart and old-lease denial. This is a prerequisite for future ENG-01 worker orchestration, not an implementation of ENG-08..11 visual engines.

The frozen Phase-02 API inventory is explicitly tracked: 2 operations have a local harness; 39 remain unimplemented, all 41 \`NOT_RELEASED\`. Run \`python scripts/validate_phase04.py\` from repository root.


## OIDC + PostgreSQL integration branch (newer than local-only section above)

The **separate** \`abc_foundation.server_oidc\` entry connects a pinned RSA-signed OIDC access-token verifier with PostgreSQL membership/RLS session persistence. It remains loopback-only and refuses to start without \`ABC_ENV=OIDC_PG_LOOPBACK_INTEGRATION\`, \`ABC_OIDC_ISSUER\`, \`ABC_OIDC_AUDIENCE\`, \`ABC_OIDC_JWKS_URI\`, \`ABC_PG_DSN\`. This is a staging harness, **not production ingress or a public IdP connection**.

The PostgreSQL test path uses \`migrations/0001_postgres_core.sql\` and \`0002_checkpoint_audit.sql\` in an ephemeral Postgres 16 service. OIDC tests sign JWTs with fresh in-memory test RSA keys and never issue public auth tokens. The specialist's tenant, role and branch must come from active DB memberships, never untrusted JWT attributes. Consent \`ACTIVE\` is not actionable without externally verified proof; \`has_verified_consent\` is read-only, and public consent/media endpoints still fail closed.

**Full technical and security review:** \`docs/04-platform/IDENTITY_POSTGRES_CONSENT_AUDIT_2026-10-29.md\`.

The \`requirements.txt\` library versions are currently major-bounded, **not a production lockfile**. Dependency locking, security scanning, cloud secrets and ingress controls must be added before deploying.


## Independent event projection process (staging proof)

Separate outbox reconciliation and session-index processing now reside in \`abc_foundation/pg_outbox.py\`, \`abc_foundation/session_index_consumer.py\` and executable \`abc_foundation/service_session_index.py\`. They run with an **independent restricted PostgreSQL worker credential** — never the HTTP \`abc_app\` role — and require an **active admin-provisioned tenant subscription**. Job leasing, replay and a non-PII read-model projection are persisted; duplicate replay is idempotent after a crash between effect and ACK.

For a disposable PostgreSQL staging environment only, following administrative migration and subscription setup:

\`\`\`bash
cd runtime/phase04
export ABC_ENV=OIDC_PG_LOOPBACK_INTEGRATION
export ABC_WORKER_DSN='<test-only worker connection secret>'
export ABC_CONSUMER_ID='<admin-provisioned consumer ID>'
python -m abc_foundation.service_session_index
\`\`\`

**No public port, no real customers, no automatic subscription provisioning.** Real per-workload service identities, protected secrets, monitoring, distributed scheduling, legal retention and live cloud infrastructure are not deployed. Purpose-scoped consent remains a verified-read-only gate; \`0005_consent_lifecycle.sql\` adds bounded validity and auditable immutable status transitions, not actual in-salon capture or attestation.

See \`docs/04-platform/DURABLE_EVENTS_AND_SERVICE_BOUNDARIES.md\` for isolation decisions, test matrix and release blockers.
