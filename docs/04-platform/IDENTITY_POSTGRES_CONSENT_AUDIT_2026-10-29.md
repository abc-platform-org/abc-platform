# ABC Phase 04 — Identity, PostgreSQL, consent and runtime integration audit

**Date:** 2026-10-29  
**Scope:** existing Phase-04 draft PR #23, branched from the accepted P00–P02 *design-only* baseline. Phase-03 PR #21 remains independent/draft.  
**Classification:** STAGING_INTEGRATION_CODE_TESTED — NO LIVE IDP, CLOUD DATABASE, PUBLIC INGRESS OR CUSTOMER DATA.  
**Product release:** NOT_AUTHORIZED. Formal Phase 04 exit: IN_PROGRESS.

## 1. Trust boundary and intended architecture

\`\`\`text
External OIDC identity provider (not yet connected)
  → signed RS256 JWT / pinned issuer, audience, JWKS URI
  → abc_foundation.oidc.OIDCVerifier
  → Principal(issuer, subject) ONLY — ignore roles/tenant/branch token claims
  → abc_foundation.pg_store.PostgresStore
  → authoritative active DB membership (issuer, subject, tenant, branch, role)
  → transaction-local RLS context (tenant, branch, identity)
  → permitted session record / internal checkpoint
  → atomic idempotency + outbox events
\`\`\`

Adapters: \`abc_foundation/auth.py\` is old local HS256 fixture auth **only** and must never be used for a public service; \`abc_foundation/oidc.py\` is asymmetric verifier; \`pg_store.py\` is PostgreSQL RLS-backed domain adapter; \`http_api.py\` accepts injected verifier and adapter; \`server_oidc.py\` is loopback-only staging entry. No role dropdown or client-shared screen controls authorization.

OIDC rules:
- Fixed provider configuration; no dynamic discovery from unverified token; HTTPS pinned JWKS same host as issuer (intentionally conservative; a provider with cross-host JWKS needs a reviewed exception).
- RS256 only; require \`kid\`, \`sub\`, \`iss\`, \`aud\`, \`iat\`, \`nbf\`, \`exp\`; bound token size; invalidate malformed, wrong-key, expired, unexpected algorithm/issuer/audience.
- No browser-initiated privileged token-mint route. A \`Principal\` does not carry trusted business roles.
- Real IdP setup, authentication UX, PKCE/MFA, logout/revocation/disabled accounts, session cookies, client type policies, key rotation ops, service-to-service credentials and security review remain unimplemented.

## 2. Database ownership, migrations and RLS

\`migrations/0001_postgres_core.sql\`: tenants, branches, active membership registry, sessions, idempotency journal, outbox, consent evidence; \`0002_checkpoint_audit.sql\`: checkpoint state audit. Applied to ephemeral PostgreSQL 16 through a privileged **CI-only** migrator. The runtime DB role \`abc_app\` has neither SUPERUSER nor BYPASSRLS nor schema write privileges.

RLS: \`FORCE ROW LEVEL SECURITY\` on scoped tables, including tenant/branch directory, membership self-view, assigned specialist session, idempotency, consent evidence and checkpoint audit. The API additionally checks membership. Transaction-local settings never come from an unverified JWT claim; they are set **after querying the authoritative active membership registry** using the verified issuer + subject. No SQL query is composed using unescaped request text.

**Defense-in-depth limitation:** PostgreSQL custom GUC values are settable by a SQL caller. Hence RLS with \`current_setting\` is not a substitute for preventing arbitrary SQL execution or protecting DB credentials. The \`abc_app\` credentials must remain server-side, privileged identities separated, all SQL parameterized, and native Postgres role/RLS adversarial tests mandatory. This is *not* a claim of full tenant isolation under a compromised privileged DB role.

PostgreSQL currently implements:
- \`createConsultation\`: persistent scoped record, exact replay or conflict, atomic canonical \`SESSION_CREATED\` event.
- \`getConsultation\`: read only when active DB membership and assigned specialist scope match.
- Internal \`/_foundation/v0/.../pause|resume\`: \`CREATED ↔ PAUSED\` state machine subset, CAS, audit and idempotency; **not an approved public v1 operation or extra v1 event**.
- NOT yet PostgreSQL-backed: durable visual-job worker, full workflow state machine, outbox publisher delivery, 25-event consumers, distributed coordination, all remaining 39 v1 API operations.

## 3. Purpose-scoped consent and image policy

\`abc.consent_evidence\` records \`client_id\`, \`session_id\`, \`tenant_id\`, \`branch_id\`, \`purpose[]\`, \`evidence_digest\`, \`disclosure_version\`, \`retention_policy_id\`, verification and withdrawal timestamps. The \`abc_app\` role has **SELECT only**, no insert/update or permission to self-assert customer consent.

\`PostgresStore.has_verified_consent\` returns **false unless** all requirements match:
- assigned specialist's currently authorized session/branch and canonical client identity;
- purpose is an allowed exact purpose (CAPTURE / AI_PROCESSING / PREVIEW_STORAGE / INTERNAL_HANDOFF);
- evidence is \`ACTIVE\` with recorded verification time, digest and retention policy, not revoked;
- consent record belongs to exactly the same session/tenant/branch/client.

A CI administrator inserts synthetic evidence to test the distinction between PENDING → ACTIVE → WITHDRAWN and wrong-client/unknown-purpose denials. **This is not a real client consent workflow.** No actual signature/evidence attestation verifier, lawful processing basis, consent withdrawal API, DSR/deletion orchestrator or retention schedule has been deployed. Therefore the consent REST endpoint continues returning 501; image intake, object store and generation remain disabled. No actual customer photos can be processed.

## 4. Exact scope and CI evidence

Automated CI:
- Historical Python local-runtime suite: 36 tests.
- OIDC asymmetric-signature and failure tests: 12 cases.
- Real PostgreSQL migration + RLS + durable session/consent/checkpoint tests: 16 cases.
- HTTP OIDC/PostgreSQL e2e tests: 6 cases.
- **Total: 70 tests**, subject to verification on each exact commit. Tests do not equal a security pentest.
- \`scripts/validate_phase04.py\`: 41 P02 operations mapped; 2 local/integration-harness operations, 39 unimplemented; none released.

CI provisioning: ephemeral Postgres 16 service; a migration-only superuser and a restricted \`abc_app\` credential with dummy CI secret, never a real production credential. \`python -m unittest discover -s tests -v\` from \`runtime/phase04\`. CI must succeed at the **final PR head SHA**; past passing runs cannot certify subsequent modifications.

## 5. Risk/defect disposition

| Risk | Current mitigation | Outstanding |
|---|---|---|
| JWT signature/algorithm substitution | RS256 and pinned JWKS, fail closed | Live provider, keys/rotation/revocation, MFA |
| Role/tenant spoofing via client token | Claims ignored for authorization, authoritative active DB membership | Full RBAC/ABAC roles and per-purpose field projection |
| IDOR / cross-salon reads | Scoped SQL and FORCE RLS; tests | Production breach/penetration, security posture |
| Stale checkpoint / duplicate commands | PostgreSQL CAS, idempotency and row locks | Full ENG-01 state graph, distributed workers |
| Consent self-assertion | Restricted table writes, verification gate | Independent customer evidence verifier, withdrawal and DSR |
| Raw image exposure | No media endpoints enabled | Encrypted media store, signed time-bound URLs, image policies |
| Outbox delivery | Atomic SESSION_CREATED event | Async publish/retries/DLQ, consumer acknowledgements, service graph |
| Production readiness | Loopback-only server; no live data | Infra-as-code, deployment, TLS ingress, rate limits, secrets, audit/monitoring, DB backup/restore |
| Software supply chain | CI package install/test | Lockfile/SBOM/scanning/reproducible builds, approved dependency inventory |

## 6. Release and architecture decisions

- Separate internal design acceptance (P00–P03), this Phase04 integration slice, and later product-release gates G06/G08/G09.
- No mutation of frozen P02 v1 OpenAPI, event schemas or state contracts from this PR.
- The 19 engines remain individually owned architectural responsibilities, not 19 live agents or a collection of GPT prompts; services must have typed interfaces and independent test gates when implemented.
- Provider-neutral adapter is intentional because no production IdP issuer, verified organization/tenant account, deployment environment or genuine secrets are connected.
- Do not merge PR #23 as "Phase04 complete" or deploy with real customers before external environment and qualified security/privacy review.

**Next implementation order:** real staging IdP registration + managed Postgres + server IAM, consent attestation and withdrawal, encrypted object storage, durable distributed outbox/job workers, per-engine service contracts/observability, rollback + security review. All must have exact test evidence and named owners.
