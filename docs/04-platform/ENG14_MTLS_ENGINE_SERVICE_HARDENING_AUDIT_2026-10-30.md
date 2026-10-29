# ABC — ENG14 State Enforcement, Workload mTLS and ENG04–06 Independent Engine Processes

**Engineering audit:** 2026-10-30  
**Scope:** branch `security/eng14-workload-mtls-engine-isolation-20261030`, draft PR #36 stacked on #35 → #34 → #33 → #32 → #31 → #29 → P04 PR #23. Protected `main` and Phase02 `contracts/v1` unchanged. **Not a production release approval.**

## A. Real modifications

### A1 — ENG14 enforcement at every defined transition

- `ENG14TransitionPolicy` loads the frozen 20-state/102-edge consultation graph. It deterministically returns an ALLOW or BLOCK decision for **all 102** canonical transitions; only `CREATED → PAUSED`, actor `SPECIALIST`, guards `authenticated_actor` and `persist_checkpoint`, is allowed under **S0/synthetic scope**. Other 101 edges stay **BLOCKED**, not silently approved or claimed as implemented.
- PostgreSQL migration **0014** installs a first-authority `eng14_state_transition_gate` BEFORE UPDATE trigger. It rejects invalid source/target/version, forged actor/session scope, assignment changes, and missing active specialist membership, and records a version-bound audit in the same transaction. A failed transaction rolls the audit back.
- A second defense removes `abc_app`'s table-level `UPDATE(state,checkpoint)` privilege entirely; the remaining metadata-only UPDATE privilege cannot mutate the state. **Both** prior operational code paths — `PostgresStore.checkpoint_command` and `ENG01PostgresCommandStore.execute_eng01_pause` — now call the narrow `SECURITY DEFINER abc.eng14_apply_pause(session,expected_version)` broker, which rechecks trusted scope and active specialist membership before a CAS-style checkpoint. The trigger independently reviews that broker's update. No caller-generated `policy_decision_id` can approve a state mutation.
- The known unsafe `resume` remains fail-closed with 501. S1/S2/S3 professional safety approvals, consent-validity-by-purpose, specialist qualification and authorization for other 101 edges do not yet exist; no changes to the canonical v1 graph.

### A2 — Identity and actual encrypted network execution boundary

- `service_mesh_identity.py` validates RS256 JWKS-signed short-lived service JWTs against pinned **external HTTPS issuer**, dedicated audience, expected engine and consumer, bounded lifetime/jti, **client certificate DER SHA256 thumbprint** and an exact SPIFFE-style URI SAN in the peer certificate.
- `require_mtls_context` enforces TLS 1.3 minimum and mandatory peer certificate verification. It needs externally supplied key/cert/trust anchors; no CA, secret, keypair or issuer is bundled or silently generated in product code.
- `private_engine_transport.py` supplies a real framed TLS socket port with strict 256-KiB request/response limits, authorization before dispatch and explicit cross-consumer denial. Its only approved bind is **127.0.0.1**, never the public network. `private_engine_service_server.py` allows launching one target engine per stand-alone OS service process, but refuses production/public start, unprovisioned certificate material or an unapproved loopback/engine configuration.
- `managed_engine_client.py` is the matching remote engine-call adapter; the token must come from an **injected external managed workload token provider**. The client validates exact response request ID, engine ID, consumer, session, contract version and nonreleased status. There is no plaintext fallback.
- PG worker identities from PR #35 remain per-consumer NOINHERIT authenticated logins, independent from service JWT/transport identity. Neither one alone supplies authorization on the other side. **Real managed identity issuer, workload enrollment, CA rotation, private service mesh and externally managed secrets have NOT been created or deployed**. This is a fully runnable local TLS integration prototype with a deployable interface, not verified production mTLS.

### A3 — Separate ENG04, ENG05, ENG06 executable boundaries

- `isolated_engine_service.py` serves exactly one engine ID per process and validates a versioned request/response envelope; refuses unknown/oversized/malformed fields, unsupported versions and client content that attempts to impersonate an engine.
- `internal_engine_ports.v1.json` gives each engine its own input-shape restrictions under a strict shared envelope, with JSON Schema Draft 2020-12 validation. The frozen `contracts/v1` remain unchanged.
- `isolated_engine_runner.py` calls `ENG-04`, `ENG-05` and `ENG-06` via **three separate OS child processes**, with no shell, bounded deadline, output-size guard and a minimal environment that omits PostgreSQL DSNs, client secrets and ambient credentials. Each result must match the originating request/consumer/session exactly.
- `eng04_06_pipeline.py` now invokes these three isolated engines in order but keeps the preexisting **durable PostgreSQL pipeline orchestration/ACK in one authorized Worker transaction**. A crash or incomplete sequence must not ACK a job. The original ENG03 source provenance/ENG14 answer policy and evidence controls remain intact. The network mTLS adapter is tested separately; **the existing PG worker's default route is the three-process local adapter, not yet a hosted network mesh**.
- Separate long-lived mTLS listeners can be started from `private_engine_service_server.py` **locally only** with external certs/tokens. They have not been deployed as independent Render/other cloud services.

## B. CI evidence

- Tests now include: all 102 machine transitions, tampered policy and forbidden actor, direct SQL state UPDATE with/without forged session GUC, broker audit/replay, revoked membership, typed ENG01 command and concurrency, isolated ENG04/05/06 port schema and secret-environment denial, real TLS1.3 localhost handshake with a test-only CA/cert chain and RS256 token, wrong thumbprint/identity/consumer/expired token, real remote client test, no public listener, inherited baseline 231+ PG16 tenant/provenance/DLQ tests and the Docker non-root/fail-closed checks.
- The last exact-head CI commit/run must be recorded **only after** GitHub Actions verifies it. Past FAILED runs exposed: inaccurate expectation for RLS-hidden row; old ENG01 typed pause command still doing direct table UPDATE after column privilege revocation. The typed command was corrected to use the same broker; no prior failed attempt counts as a pass.

## C. P0 / P1 open blockers (strict)

| Gate | Current evidence | Status |
|---|---|---|
| Local state transition control | SQL broker + trigger + 102-edge policy matrix | CI candidate |
| Approved S1–S3 policy and qualified human review | No professional rules/consent evidence sufficient | BLOCKED |
| JWT issuer/managed workload identity | Pinned verifier implemented; no real issuer provisioned | BLOCKED |
| mTLS/private network | Real loopback TLS1.3 with ephemeral CI certs only | BLOCKED for cloud |
| ENG04/05/06 OS isolation | Three process-local engine ports + versioned schema | CI candidate |
| Independently deployed network engines | Loopback network prototype only, no production mesh/rollout | BLOCKED |
| PostgreSQL identity across trust boundaries | Scoped logins/roles; DB broker still trusts OIDC GUC tied to application service authentication | Independent pen test required |
| Sensitive salon client data | Synthetic-only, no images or actual consultations | BLOCKED |
| Production cloud, cost, observability, restore, SLO | Not provisioned or certified | BLOCKED |

Further execution requires an approved managed identity provider and certificate authority, a provisioned private network, isolated long-running engine service deployments, mTLS token exchange and rotation, authenticated service-to-DB attestation, complete S0–S3 expert policy/consent and verifiable qualifications, explicit privacy controls, penetration and chaos tests, and real staging security signoff **before** any real-client access.

**Disposition:** `P04=IN_PROGRESS`; `ENG14_ALL_EDGES_COVERED_AS_ALLOW_OR_BLOCK`, not `ALL_EDGES_IMPLEMENTED`; `MTLS=LOCAL_TEST_HARNESS`, not `MANAGED_CLOUD_IDENTITY`; `ENG04/05/06=SEPARATE_SYNTHETIC_PROCESSES`, not `DEPLOYED_INDEPENDENT_SERVICES`; `RELEASE=DENIED`. No paid API, no deployed cloud resources, no merge to `main`.
