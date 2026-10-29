# ABC — Private Workload Network and ENG04/05/06 Separation Runbook (NO DEPLOYMENT)

**Status:** implementation/test candidate; production and real-client use BLOCKED. Date 2026-10-30. Stack PR #36 on #35. This guide never authorizes external billing, real PII or a release.

## 1. Security ownership and prerequisites

**Platform governance owner:** approves S0–S3 policy rules, audit signoff, retention/consent purposes, incident response, deploy budget, private-region placement, qualified specialist actions.

**Infrastructure/security operator:** provisions a trusted managed workload issuer and JWKS URL, a private certificate authority (CA), distinct engine identities, a private-only network segment, managed secret delivery, revocation and rotation, monitoring, backup/restore. None is provisioned by this repo. Never paste private keys/tokens into GitHub, logs, ChatGPT or the repository.

**Per-engine owner:** runs one `ENG-04`, `ENG-05`, or `ENG-06` target in a separate OS user/container/process with locked-down network policy, non-root UID, read-only filesystem, controlled egress and hard service-to-service authorization. The supplied CI path has separate processes but shares its host user and is **not an isolation security sandbox**.

**Database operator:** owns managed PostgreSQL 16+ RLS and the **14 immutable migrations**, scoped secrets, role-enforced credential mapping, audit and restore tests. Consumer-bound login from migration 0013 is necessary but not sufficient for service network identity.

## 2. Identity verification contract

A verified service call requires **all** of: external RS256 JWT issuer+audience, bounded token lifetime and unique jti; exact caller engine; exact consumer/session scope; an unexpired, independently CA-validated client certificate; exact certificate URI SAN `spiffe://abc.internal/eng04/<consumer>` (in the ENG-04→ENG-05 example); the JWT `cnf.x5t#S256` equal to the presented DER certificate SHA256 thumbprint; a valid TLS1.3 private socket; an active administrator-issued consumer and engine authorization and a transactionally checked source provenance. No browser-provided or LLM-generated `actor`, `tenant`, `policy_approved` or `certificate_fingerprint` is accepted as authority.

`BoundEngineIdentity` implements token+certificate checks. A production issuer/token broker, certificate manager and workload-to-database binding have **not** been deployed. The current testing authority is ephemeral and exists solely inside CI. Add certificate/key rotation with overlapping trust anchors, trust-revocation tests, JWKS outage behavior, enrollment and audit before deployment.

## 3. Executable local-only service wiring

The three service implementations can be launched individually with `python -m abc_foundation.private_engine_service_server`. Their start requires:

```
ABC_ENV=LOCAL_INTEGRATION_ONLY
ABC_NETWORK_BOUNDARY=LOOPBACK_ONLY
ABC_ENGINE_SYNTHETIC_ONLY=true
ABC_ENGINE_ID=ENG-05
ABC_CALLER_ENGINE_ID=ENG-04
ABC_ENGINE_CONSUMER_ID=<approved-synthetic-consumer>
ABC_ENGINE_PORT=<nonprivileged-loopback-port>
ABC_TLS_CERT_FILE=<external-runtime-cert-path>
ABC_TLS_KEY_FILE=<external-runtime-key-path>
ABC_TLS_CA_FILE=<external-runtime-CA-path>
ABC_WORKLOAD_ISSUER=<https-pinned-external-issuer>
ABC_WORKLOAD_JWKS_URL=<https-pinned-external-JWKS>
```

The current server refuses public network binds and production settings; never disable the checks to expose it to real clients. `ManagedMTLSEngineClient` uses a caller-provided managed token broker, mutually authenticated TLS and immutable request-to-response scope checks. Use the internal `abc.internal.engine.synthetic.v1` request/response schemas; do not quietly replace frozen P02 API/JSON schemas. The default PostgreSQL worker still uses `IsolatedEngineRunner` to start three separate synthetic OS child processes; it is **not yet wired to three hosted services**. The network adapter and listener are independently integration-tested with TLS but not deployed.

## 4. State safety and ENG14 failure policy

- The canonical consultation workflow has 20 states and 102 edges. ENG14's bounded synthetic policy gives a decision for each edge and **blocks 101** because the necessary qualified rules, consent evidence, engines and transition executors have not passed review.
- The only executable edge is `CREATED→PAUSED` for the currently verified specialist. DB role `abc_app` cannot modify `sessions.state` or `checkpoint` using SQL UPDATE; it must call `abc.eng14_apply_pause`, which rechecks current assignment, membership, CAS version and scope. An independent BEFORE UPDATE trigger rechecks the rule and inserts an audit record in the same transaction.
- ENG01 typed commands, direct internal checkpoint calls and idempotent replay use the **same DB broker**. `PAUSED→CREATED` (resume) is disabled until an atomic verified consent/policy procedure exists. No bypass for emergencies without a formally designed audited emergency path.
- Full safety policy S0–S3 for real hair/skin/nails/etc, qualified specialist approvals, service-specific material contraindications, client consent revocation, DSR and stop/recovery conditions are a separate P0 implementation, not described as complete by the 102-edge block matrix.

## 5. Adversarial exit checks for production staging

Require signed independent review of TLS interception and trust rotation, wrong peer CA and certificate chain, expired/revoked certificate, stolen valid token with wrong TLS certificate, wrong JWT audience/issuer/kid/alg/exp, unauthorized tenant/consumer, actor privilege escalation, cross-engine invocation, request/schema replay, oversized frames and timeouts, crash/backoff/DLQ semantics, SQL state update bypass, SQL SECURITY DEFINER ownership/search_path, forced RLS, concurrent CAS, evidence provenance and consent expiry.

Also require independent OCI images/entrypoints for ENG04/05/06, separate service accounts and resource limits, private DNS and egress firewall, observable bounded request latency, OpenTelemetry source/decision trace, immutable audit ledger, sensitive data encryption at rest, secret rotation and disaster recovery drills. No such service deployment or disaster test has been completed.

## 6. Release decision and safe operating boundary

The synthetic-only code and tests demonstrate a local cryptographic transport boundary and independently runnable engine processes, **not a managed enterprise service mesh**. Preserve all release blockers until external managed issuer/CA and private network exist, then do a new threat-model and infrastructure-specific hardening review. Do not merge PR #36 into main or accept real client media/PII without approved release gates.
