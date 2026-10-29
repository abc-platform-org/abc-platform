# ABC / Phase 04 — Atomic ENG01 Session Creation, Managed Service Identity, ENG14 Specialist Policy, Private ENG04–06 Services

**Date:** 2026-10-30  
**Change set:** stacked draft PR #39 on #38 → #36; protected `main` and frozen Phase02 `contracts/v1` unchanged.  
**Purpose:** replace the unbrokered session creation path, prepare a verifiable physical PostgreSQL service-login boundary, and develop bounded specialist safety gates and private-engine service topology. **Do not interpret this as a production signoff.**

## A. Executed source changes

### A1. Transactional ENG01 SESSION_CREATED broker

Migration **0016** adds `abc.eng01_create_session(p_body jsonb,p_key text)`, a narrowly executable `SECURITY DEFINER` SQL broker which:

1. Revalidates the actor's exact tenant, branch, issuer and active specialist assignment; independently enforces the allowed create body shape and synthetic shared-display scope.
2. Computes the canonical JSONB payload digest in PostgreSQL, uses a transaction advisory lock bound to tenant + actor + intent key, and returns an unchanged idempotency receipt on exact replay or a 23505 collision error on conflicting payload.
3. Creates the only initial `CREATED/version=0/checkpoint=NULL` session, the `SESSION_CREATED` event outbox record, a scoped idempotency response, and an `eng01_create_audit` row in **one PostgreSQL transaction**. If a component fails, nothing is committed.
4. Revokes direct `abc_app` `INSERT` on `abc.sessions` and `abc.outbox`; an independent invoker trigger rejects forged direct `operation=create` receipts. Legacy `PostgresStore.create` now uses only the broker and checks postconditions.
5. Preserves the earlier ENG14 guarded `CREATED → PAUSED` route and the existing v1 product contract. Consent is **not** implied by session creation.

The migration also registers an administrator-controlled `eng01_api_login_bindings` table. The broker uses immutable PostgreSQL `session_user` to allow a separately authenticated, active, tenant-scoped physical service login. Custom `abc.*` GUC values are **not service identity credentials**. The original `abc_app` direct login remains a **legacy synthetic test path** pending a managed staging cutover.

**Residual limitation:** even this narrow broker does not cryptographically verify end-user OIDC identity *inside PostgreSQL*. That verification still occurs in the trusted application gateway; theft of its DB credential remains critical. No managed login/certificate is actually enrolled. The existing ENG14 pause broker has not been cut over to managed service logins; real staging rollout must remain blocked until the entire state mutation surface is identically bound.

### A2. Managed PostgreSQL client transport preflight

`managed_db_identity.py` enforces dedicated `abc_api_*` login names, `sslmode=verify-full`, client certificate, key, pinned server root CA, private `.internal`/`.private` host and staged database scope. A separate live-connection check compares real `session_user`, `current_user`, TLSv1.3, client DN and issuing CA DN using `pg_stat_ssl`.

These are testable **admission primitives**, not proof that a deployment exists. The PostgreSQL operator must independently enforce `hostssl ... clientcert=verify-full` and a fixed `pg_ident` certificate-to-login map, role `NOINHERIT` / `SET ROLE abc_app` grants, per-tenant enrollment/revocation, secret rotation, role and policy checks, read-after-revoke and compromise-response testing. Client-supplied `SET config`, environment flags or token text cannot substitute for this server-side admission. Provider metadata and enrolled CA are not available.

### A3. ENG14 professional policy: S1–S3 review candidate, not permission

`eng14_professional_gate.py` provides explicit conservative S1/S2/S3 service evidence requirements for haircut, hair color, keratin, skin, nails, beard, makeup, extensions and corrective services. All evidence must match tenant/session/version and carry a traceable digest/source. Missing evidence, mismatches and unknown service profiles are blocked. Even a fully populated evidence packet and caller-supplied `approved=true` **never authorize professional treatment, operational handoff or a state transition**. Actual independent qualified-specialist registries, approved SOP versions, consent-purpose and revocation evidence, material/chemical contraindications, exception protocols and human approval binding are unimplemented, and therefore **BLOCKED**.

Existing canonical 20-state/102-edge ENG14 matrix remains intact: only the non-treatment synthetic `CREATED→PAUSED` state edge is allowed. All other edges are explicitly blocked pending distinct executable security controls.

### A4. Three private-engine executable service candidates

`private_engine_service_server` and `private_engine_transport` now support a separate **synthetic-only private-staging** mTLS listener with mandatory TLS 1.3, external trusted CA, externally issued RS256/JWKS workload token and exact caller/consumer binding. The trusted private mode is a distinct branch; the original 127.0.0.1 local integration mode remains. Managed client endpoints may use pinned single-label `.internal` hostnames, never public `onrender.com` or wildcard destinations. `ENG-03` is explicitly permitted as the bound source pipeline caller.

A **non-active, auto-deploy-disabled candidate** Render Blueprint lives at `infra/render/private_engine_services.staging.template.yaml`. It declares separate ENG04, ENG05 and ENG06 **private** services and requires external secret mounts. No actual service, CA, issuer, private network route, DNS, secret manager or database has been provisioned in the linked Render workspace. The hosting provider—not an untrusted environment string—must enforce that there is no public route. No new spending or deployment was triggered.

The durable PostgreSQL pipeline continues to default to three separate synthetic local subprocesses unless an authenticated `ManagedMTLSEngineClient` is explicitly injected. Network routing is **not automatically enabled**.

## B. Verification acceptance gates

- Python/PostgreSQL CI must apply immutable migrations 0001–0016 and rerun the strict checksum staging migrator on a disposable PostgreSQL 16 service.
- Negative SQL tests must prove direct session/outbox INSERT, forged receipts, missing/revoked service-login bindings and direct state/metadata changes fail closed.
- Replay/concurrency tests must prove one session, one outbox event and one immutable creation audit row per intent.
- ENG14 test vectors must show unverified service evidence and forged human/consent approvals cannot enable any professional action.
- TLS unit/integration tests must reject public DNS, bad issuer/cert thumbprint, untrusted TLS, wrong consumer and wrong route, and verify separate private-listener configuration.
- YAML topology tests must show three private-only non-auto-deployed service definitions, no embedded secrets, no public-facing route.
- GitHub exact-head Foundation and Documentation CI must both pass before this draft is considered **CI_TESTED**.

## C. External operational gates — all still OPEN

| Gate | Owner / required external proof | Decision |
| --- | --- | --- |
| Managed DB and service issuance | SRE/Security: unique client cert/CA, physical-login enrollment, pg_hba/pg_ident, expiry and revocation evidence | BLOCKED |
| ENG01/14 end-to-end principal binding | Security: identical physical-login verification for pause/other transitions and no shared abc_app runtime login | BLOCKED |
| Production consent and privacy | Legal/Privacy: purpose-specific independently verified consent, revocation, retention/DSR audit | BLOCKED |
| Professional S1–S3 authorization | Qualified salon specialists and governance board: reviewed SOP/contraindication matrices, audited signatures and liability | BLOCKED |
| Private ENG04/05/06 deployment | Infrastructure: private service provisioning, no public edge, distinct service accounts/CA, monitored network policy | BLOCKED |
| Operational signoff | Security/Ops: pentest, load/chaos tests, backups/restore, alerting, uptime, cost controls, change control | BLOCKED |
| Public/product release | Release authority: all preceding independent gates green | BLOCKED |

**Decision:** `P04=IN_PROGRESS`, `RELEASE=BLOCKED`, `PR=DRAFT`, `main=UNCHANGED`, `REAL_CLIENT_DATA=PROHIBITED`, `PAID_API=OFF`.

## D. Recommended rollout order after external provisioning

1. Deploy synthetic-only managed PostgreSQL in a private staging account and prove both external server PKI and application client TLS identity with an independently issued ephemeral service certificate.
2. Enroll unique application worker logins and remove direct runtime access by the legacy shared `abc_app` LOGIN. Extend and retest every ENG01/14 transactional broker and RLS path against immutable `session_user`.
3. Obtain qualified service-specific ENG14 approval and independently verifiable consent evidence, implement transactionally version-bound S1–S3 authority, negative overrides and human signoff.
4. Provision three separate private services from the non-active topology after security/network and cost approval. Inject expiring trust roots, external workload issuer and scoped token broker; run actual private-network E2E and rollback tests.
5. Sign off observability, tenancy, data protection, incident response, recovery, load and penetration tests before considering a release.

**No approval or deploy action is implied by this runbook.**
