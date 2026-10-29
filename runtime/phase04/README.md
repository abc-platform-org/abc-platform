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
