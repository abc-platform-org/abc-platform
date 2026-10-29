# ABC — ENG14 Transition Enforcement, Service mTLS and ENG04–06 Isolation
**Audit cut:** 2026-10-30 (local code review, no customer deployment)  
**PR:** [#36](https://github.com/saleheebrahimi2029-hub/abc-platform/pull/36) (DRAFT, stacked on #35); protected `main` unchanged.  
**Code verification:** [Foundation CI #40960163876](https://github.com/saleheebrahimi2029-hub/abc-platform/actions/runs/40960163876), code commit `7b7cf20bf623edf61cc029b8d9f44d1f3c45d803`: **SUCCESS 255/255 Python tests**, PostgreSQL 16 migrations **0001–0014**, migration checksum and repeatability, zero-paid-API synthetic walkthrough, non-root Docker, local TLS certificates and negative-token tests.  
**Release state:** **NOT APPROVED.** This is synthetic-only engineering evidence.

## What actually changed

### 1. ENG14 / ENG01 state write authority
- All **102 frozen canonical CONSULTATION_SESSION transitions** receive a deterministic policy decision, default **BLOCK**. Only the narrow operational **CREATED → PAUSED** path is marked `ALLOW` at synthetic **S0**; no consent, specialist treatment recommendation, `resume`, look selection, handoff or higher-tier S1–S3 transition has been implemented or approved.
- Migration `0014_eng14_state_guard.sql` adds an independent `BEFORE UPDATE OF state` trigger on `abc.sessions`, a tightly scoped `eng14_apply_pause(session_id, expected_version)` security-definer broker and a durable `eng14_state_guard_audit` table. The SQL policy validates a current specialist membership, tenant/branch, state/version and legitimate transition in the same transaction.
- `abc_app` **loses direct table-wide UPDATE rights** to `sessions.state` and `sessions.checkpoint`; it retains narrow non-state metadata rights. `PostgresStore.checkpoint_command` now calls the SQL broker, and the independent trigger executes before the state is committed. Session CAS, ENG14 evidence, state audit and idempotent receipt are atomic; an invalid direct SQL UPDATE is denied by PostgreSQL privileges.
- `PAUSED → CREATED` remains **disabled** until an independently verifiable, version-bound consent and current-risk policy path is implemented.
- **Residual critical limitation:** active specialist/tenant context is conveyed into `abc_app` as custom PostgreSQL settings set by a server verifying OIDC. This is *not cryptographic per-user DB identity*. A compromised `abc_app` credential plus forged custom settings may invoke the policy broker for a legitimately active specialist; signed human identity must be bound inside a separate authorized service/transaction before any customer data or non-S0 transition is enabled. The privilege-restricted broker reduces attack surface but does **not** close this threat.

### 2. Internal workload identity & network
- `service_mesh_identity.py`: RS256/JWKS verification of a short-lived service JWT with pinned issuer, target audience, engine and consumer identifiers, UUID token ID, certificate SHA-256 thumbprint confirmation and exact URI SAN identity. No code mints tokens or issues production certificates.
- `private_engine_transport.py`: **actual TLS 1.3 mutual-certificate** server and client over bounded length-delimited JSON frames with certificate verification and token-binding. Only `127.0.0.1` is permitted for the prototype. Tests generate a **temporary CI CA**, host/client certificates and asymmetric JWT signer to demonstrate handshake and reject wrong engine, wrong consumer, mismatched thumbprint, omitted token, and invalid token lifetime.
- `private_engine_service_server.py`: individually runnable private mTLS **process entrypoint per target engine**, configured by externally sourced certificate/key/CA and signed JWKS issuer, refusing non-local and non-synthetic modes. No managed identity provider, KMS, production trust bundle, network segment or managed workload rollout has been created.
- Existing PR #35 per-consumer PostgreSQL LOGIN NOINHERIT / FORCE-RLS bindings remain the database authorization layer. Local CI certificate verification is *not* a production SPIFFE/SPIRE or service-mesh deployment.

### 3. ENG04/05/06 dedicated process boundaries
- `isolated_engine_service.py` and `isolated_engine_runner.py`: ENG04 analysis, ENG05 knowledge retrieval and ENG06 conditional decision run as **three distinct subprocesses**, not three in-process function calls.
- Each request and response uses versioned `abc.internal.engine.synthetic.v1` contracts, validated by JSON Schema 2020-12 in `internal_engine_ports.v1.json`, with explicit engine ID, UUID request/session, consumer, allowed payload shape and `release_approved=false`.
- Calls have size limits, 8-second default deadline, no shell or inherited parent database DSN/credentials, strict process exit and response checks. The independent PostgreSQL pipeline process remains responsible for ENG03 evidence lineage, leases, result persistence and ACK in one transaction.
- Separate **network listeners are implemented as local guarded prototypes**, but the primary CI pipeline still launches ENG04/05/06 as child processes. This is *process isolation*, not independently deployed cloud microservices with per-engine scaling, availability, budgets, and monitoring.
- The domain engines still process labelled synthetic answers/fixture, not salon images or verified clinical/professional knowledge.

## CI and negative proof
- Canonical graph coverage (20 states / 102 transitions); only S0 pause approved; other edges and actor forgery rejected.
- PostgreSQL direct state-update denial, CAS race/replay, policy audit exactly once, revoked specialist, disabled resume.
- Real ephemeral TLS 1.3 mutual certificate handshake + signed workload JWT certificate binding; wrong/missing credentials, untrusted consumer/engine, lifetime checks.
- Independent engine process envelope, JSON schema and timeout/size validation, no inherited DB secrets, safe unknowns and source-only suggestions.
- Full existing ENG02 answer → ANSWER_RECORDED consumer → ENG03 lease/evidence → three subprocess engines → ENG06 conditional decision → durable PostgreSQL result and ACK regression.

## Explicit unresolved release blockers
1. Real managed service identity issuer, mTLS certificate automation/rotation/revocation and private hosted network are **not provisioned**. A real provider selection, account/security approval, budget and safe secrets remain prerequisites.
2. The privileged ENG14 pause broker still relies on `abc_app` application-context GUCs for human identity. Service-side attestations must be tamper-resistant and linked to verified OIDC claims; a stolen `abc_app` secret and forged attributes are a critical residual risk. Verify this through independent penetration and managed-role staging exercises.
3. Full ENG14 risk tiers **S0–S3** are not authorized for all canonical transitions; 101 edges remain blocked, not silently opened. Professional specialist approval, comprehensive consent/withdrawal, and policy revocation are incomplete.
4. ENG04 actual image analysis, specialist-reviewed ENG05 ontology and ENG06 production decisioning are not ready. The new engine processes are not deployed as three independent cloud services; their local mTLS listeners have not been load-, resilience-, or ops-tested.
5. The frozen v1 engine contracts are unchanged. Internal synthetic ports are draft-only; their mapping to versioned release contracts, governance, privacy, retention/DSR, cross-tenant chaos, backups/restore, performance, encryption/secrets, cost and independent security sign-off remain open.

**Final gate:** `ENG14_DB_S0_PAUSE=CI_TESTED`, `MTLS_LOOPBACK=CI_TESTED`, `ENG04_05_06_SUBPROCESSES=CI_TESTED`; `MANAGED_CLOUD_IDENTITIES=NOT_DEPLOYED`, `ENG14_FULL_S0_S3=BLOCKED`, `ENG04_05_06_CLOUD_SERVICES=NOT_DEPLOYED`, `P04=IN_PROGRESS`, `RELEASE=BLOCKED`.

No change to `main`; draft PR requires independent code/security review and a successful exact-document-head CI before merge.
