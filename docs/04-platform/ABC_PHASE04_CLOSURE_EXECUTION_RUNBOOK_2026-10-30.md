# ABC Phase04 — Closure Execution Runbook / Release Blocker Inventory

**Date:** 2026-10-30  
**Environment:** synthetic-only / local CI. **Status:** PHASE04=IN_PROGRESS, RELEASE=BLOCKED.  
**Never:** deploy a public web service as a private engine substitute; treat a CI certificate as a managed CA, or put real salon photos, bearer tokens, private keys, connection strings or specialist identity documents into GitHub.

## 0. Stacked PR and architecture baseline

Unmerged **draft** dependency chain from earlier work (each branch stacks on the previous):
1. PR #40 ENG14 managed identity.
2. PR #41 PG16 physical TLS clientcert test and isolated engine TLS testing.
3. PR #42 private API application mTLS.
4. PR #44 EDOC-01 seven engines × ten independent gates.
5. PR #46 ENG04/05/06 v2 architecture and three-column in-salon AI Studio.
6. PR #47 actual bounded ENG04/05/06 isolated Python engines.
7. PR #49 pixel-level real-image QA and Ed25519-signed professional-source gate.
8. **This PR #50:** durable PostgreSQL anti-replay (migration 0018), verified physical managed DB login, authenticated local-only v2 ingress, Phase04 acceptance record.

No drafts are merged to protected `main`. Promote only in sequence after security review, approved v1/v2 compatibility, checked migration receipts, fault tests and signed change control.

## 1. Changes implemented in this PR

- `0018_eng14_distributed_replay_ledger.sql`: transactionally unique sha256 token replay fingerprint across tenant, issuer and audience, mandatory server-side tenant-workload policy, no application DML, forced RLS, 5-minute maximum expiry and operator-only cleanup/receipt ownership. It is applied and journaled by the staging migrator, with checksum pinned in migration receipts.
- `distributed_replay.py`: caller-independent UUIDv4, issuer/audience/expiry boundary; independent PostgreSQL connections must agree on one winner under concurrent claims, including different tenant IDs.
- `service_mesh_identity.py`: returns **cryptographically verified** issuer/audience/expiry as well as certificate-bound JTI for replay ledger. No token minting.
- `eng01_v2_authenticated_ingress.py`: strictly *local-integration-only* composition of external certificate/JWT verifier → authenticated tenant/session/state-version authorization → DB-backed one-time token claim → v2 schema-bounded engine. It is not a deployed HTTPS endpoint, cannot mint trust and forbids customer deployment.
- `staging_api.py`: managed DB active role remains **abc_app after SET ROLE**, while the physically authenticated `session_user` must equal the exact configured managed login. Both are validated; neither relies on caller GUC. The original active-role name is intentional.
- Tests: PostgreSQL 8-connection atomic race, cross-tenant token reuse, expiry and physical-managed-mode refusal, scoped v2 policy admission, bad certificate/identity, wrong tenant, test-only fixture replay, and no production environment dispatch.
- `governance/phase04_readiness.v1.json` + validator: ten physical/operational closure gates all OPEN, anti-false-COMPLETE test.

All these code tests are necessary, not sufficient, for live environment readiness.

## 2. Operator-controlled commissioning, strictly in order

### 2.1 Infrastructure approval — NO PROVISIONING YET

Operator and owner must document external provider/account/region, approved service topology and monthly budget, scope, cloud identity ownership and rollback contact. The connected Render API only offers public `web` creation and standard managed Postgres; it **cannot** provision the required `pserv` private service nor demonstrate PostgreSQL physical mutual TLS via its normal instance configuration. Therefore **do not use that API as a substitute**. No infrastructure/resource IDs can be attested yet.

### 2.2 Managed CA, private database and credentials

External security operator provisions per-service TLS1.3 certs/key vault, exact SAN and permitted peers, JWKS OIDC issuer/rotation, expiry+revocation drill. Database operator provisions independent PostgreSQL16 private host with `hostssl` `clientcert=verify-full`, client `sslmode=verify-full`, server CA pinning, per-workload physical logins with `NOINHERIT`, `abc_app` scoped `SET ROLE`, and ledger 0018 after migrations 0001–0017. Verify physical `session_user`, `pg_stat_ssl.client_dn/issuer_dn/client_serial`, `FORCE ROW LEVEL SECURITY`, managed tenant mode and denied shared login. Dump only redacted non-secret proof.

### 2.3 Independently deployed PRIVATE API and engines

Operator provisions four independent private services: API, ENG04, ENG05, ENG06 (and background ENG03 worker) with distinct workload identities, isolated lifecycles, nonpublic networking and separately rolled revisions. Validate exact private DNS/SAN binding, no ingress from internet, external mTLS issuer and audience, least privilege and secrets policy. Legacy `abc.internal.engine.synthetic.v1` is deliberately separate from `abc.internal.engine.v2.draft`. **Do not enable live v2 processing** merely by setting an environment flag: its authenticated private network server, DB-backed authorization and independently verified consumer contracts still need to be written and approved.

### 2.4 E2E and regression evidence

Run with synthetic data only:
- Valid JWT and mTLS admission, then mismatched peer, issuer, audience, certificate, revoked/expired issuer, duplicate JTI and wrong tenant/branch/session/version.
- At least two real replicas with same PostgreSQL replay ledger, exactly one token accepted; rolling deploy and token renewal, outage and cert rotation.
- ENG02 consent create/revoke, ENG03 Claim/Lease/ACK, retry exhaustion/DLQ, worker crash/restart, idempotency and replay under reconnection.
- ENG04 visual pixel QA on synthetic generated PNGs; ENG05 signed-current-source policy; ENG06 SOP and human review gates; **no real procedures or customer media**.
- Document actual service IDs, deployed image SHA, migration receipt hashes, run IDs, p50/p95/p99 and errors, database backup/restore evidence, runbook/alerts/incident response.

### 2.5 Independent authority and release decision

- Specialist/reviewer with independently verified credentials signs service SOP, version/expiry, contraindications and stop conditions; operator signs issuer roster ownership; privacy officer signs consent, retention, erasure, legal boundary and security test results.
- Independent security and professional reviewers verify all engine G01–G10 evidence plus ten `P04-01..10` phase closure gates.
- Only then can a separately reviewed release authority PR switch `phase04_complete=true`. The code baseline validator *intentionally* rejects such a claim until the independent verification mechanism is integrated and acceptance is formally reviewed.
- Even PHASE04 COMPLETE **does not automatically grant customer production release**. Pilot, model visual performance and quality remain separate product decisions.

## 3. Execution sequence before the next deployment approval

**Engineer-controlled now:** freeze v2, reconcile PRs and tests; implement managed identity/replay/consent hardening, no paid inference.  
**External operator required:** provider budget, private services, external CA and physical PG, live workload signing.  
**Human specialist/security required:** SOPs, qualifications, privacy and final independent signoff.

Current source-controlled evidence is developer CI and controlled in-memory fixtures. It is **not** verified evidence of the provider, a real client's consent, or an approved salon intervention. Do not mark any of the seven engines COMPLETE.
