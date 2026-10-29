# ABC Phase 04 — Physical PKI E2E, Independent Approval, and Deployment Decision Record

**Date:** 2026-10-30  
**Workstream:** ENG01 / ENG14 DB identity, ENG03→ENG04/05/06 private transport, independent S1–S3 and Security release governance.  
**Status:** DRAFT / SYNTHETIC E2E; **NOT LIVE DEPLOYED**. Protected `main` and frozen Phase02 `contracts/v1` unchanged.

## 1. Executed code and verification boundaries

### A. Three actual OS services with TLS1.3 end-to-end

`runtime/phase04/tests/test_three_process_mtls_e2e.py` now launches **three independent OS processes** over real TCP loopback with real TLS1.3 mutual certificates, separate per-engine trusted server certs, an ephemeral trusted test CA, and externally modeled RS256 JWTs each bound to the ENG03 caller cert's DER SHA-256 thumbprint, exact target audience and consumer. The test invokes the actual ENG04 analysis → ENG05 knowledge → ENG06 decision contract through `ManagedMTLSEngineClient`, preserves uncertainty and produces **no released candidates**. All private keys are ephemeral test-only artifacts and are deleted after the test.

This proves functional port and PKI protocol integration on the runner. It does not prove Render's live private network, managed JWKS issuer availability, production CA rotation, independently scoped pods/containers, no public exposure, or real client-data permissions.

### B. Real disposable PostgreSQL 16 mutual client-certificate authentication

The GitHub foundation workflow now invokes `verify_real_pg_mtls_ci.py` after existing transactional PostgreSQL migrations and synthetic consultations. It builds a disposable test Docker image with actual `postgres:16`, issues a temporary CA and a distinct server/client certificate, requires `ssl=on`, `ssl_min_protocol_version=TLSv1.3` and `hostssl ... cert clientname=CN`. The test asserts the actual `pg_stat_ssl` server view of certificate subject/issuer/serial, checks that application GUC tampering cannot alter identity, and expects missing/wrong/untrusted client certificates, unencrypted transport, and server DNS mismatch to fail. The runner binds the container's published test port only to `127.0.0.1`.

**This CI certificate is not a production certificate.** It cannot sign an ABC release. A provider-controlled database is not deployed or enrolled.

### C. Runtime managed DB adapter

`ManagedMTLSPostgresStore` verifies the physical LOGIN/role against real server-observed TLS client identity **before** `SET ROLE abc_app`. It requires libpq `sslmode=verify-full`, explicit client/server CA, and dedicated per-service login. Any failed physical peer identity check or denied role transition closes the connection. `staging_api` selects this only with explicit `ABC_DB_AUTH_MODE=MANAGED_MTLS`; the prior shared login is disabled by default for staged server startup and requires explicit `ABC_DB_AUTH_MODE=LEGACY_SYNTHETIC` plus `ABC_SYNTHETIC_LEGACY_DB_COMPAT=true` in synthetic-only staging. No implicit managed-to-legacy credential downgrade is allowed. An externally managed physical database is still required for real use.

Production requires a separately controlled PostgreSQL instance with enforced server-side `hostssl clientcert=verify-full`, private networking, role grants, certificate lifecycle and RLS security review. Ordinary Render-managed internal PostgreSQL is **not equivalent**: see [Render database internal SSL modes](https://render.com/docs/postgresql-creating-connecting) and [PostgreSQL 16 clientcert authentication](https://www.postgresql.org/docs/16/ssl-tcp.html).

### D. Independent external governance review evidence

`IndependentSignoffEvidenceGate` requires two **distinct** pinned HTTPS issuer authorities, trusted RS256 signatures, separate professional and security reviewers, exact SHA, evidence digest, release scope, short token TTL, UUID approval and token IDs, a professional qualification and SOP reference, and security review reference. It rejects wrong/missing/expired/forged/mismatched evidence. Even two valid signatures return `release_approved=false`: successful cryptographic token verification is **not** equivalent to independently verified professional qualifications or successful physical security checks.

The approval packet intentionally has blank real reviewer, regulator, SOP and security signature fields. No AI-generated signoff, fictitious professional, or synthetic CI key may fill these fields.

## 2. Operational evidence required and owner

| Evidence ID | Owner | Source of truth / expected proof | Result at this commit |
| --- | --- | --- | --- |
| PKI-01 | SRE / independent CA administrator | Official CA issue & rotation records, certificate serial + subject, trust anchor public metadata, revocation drill | MISSING |
| IAM-02 | Identity platform / security | Real JWT issuer/JWKS, signed workload registration, token broker, key rotation and failed-token tests | MISSING |
| DB-03 | Database operator | Private PostgreSQL host, `hostssl` HBA, `pg_ident`, unique NOINHERIT logins, verified TLS server and client, point-in-time recovery | MISSING |
| DB-04 | Application security | Exact prod-like ENG01 create and ENG14 pause transactions on enrolled managed login with same physical session_user, revoked/forged creds fail | MISSING |
| NET-05 | Render / SRE | Three real `pserv` service IDs, private DNS, no public edge, distinct images and service accounts, secret mounts, TLS SAN matching | MISSING |
| E2E-06 | QA / Reliability | Live private-network three-service request, trace/ACK source provenance, retries/DLQ, rotation, outage/restore evidence | MISSING |
| PRO-07 | Qualified specialists | Signed service SOP + contraindication matrix + identity, qualification and jurisdiction evidence for S1–S3 | MISSING |
| PRIV-08 | Privacy / legal | Independent consent proof, revocation, retention, DSR and risk review | MISSING |
| SEC-09 | Independent security | Pentest, attack-surface, non-root isolation, audit integrity, cross-tenant negative tests, incident drill | MISSING |
| OPS-10 | Release authority | Cost authorization, rollback, release window, objective readiness review with independent professional+security signatures | MISSING |

## 3. Deployment order — not permission to deploy

1. Security operator selects and provisions an operator-controlled PostgreSQL hosting boundary, a managed CA / identity provider, and a single private network region. No subscription, resource or new bill has been created by this PR.
2. Enroll unique login/certificate pairs and validate genuine server-side `pg_stat_ssl` and `pg_hba` enforcement. Execute staging migrator 0001–0017 against an approved empty, backed-up staging DB. Separate the migrator from runtime credential scope.
3. Apply independently approved `eng14_tenant_workload_mode` managed switch **only after** end-to-end ENG01/14 health, revocation and tenant isolation prove strict denial of legacy shared credentials. Do not flip for real users until proven.
4. Provision ENG04/05/06 as three Render `pserv` resources in the same workspace/region with externally managed certificates and JWT issuer. Do not replace with public web services. Inject cert secret mounts and exact Render private DNS into the managed client.
5. Execute actual live private E2E, certificate and JWT rotation/revocation, cross-tenant and service-boundary attacks, lease ACK/replay, disaster recovery, load test, penetration test, and technical signoff.
6. Have authorized external professionals sign exact service-specific policies / approved SOP version and independently scoped consent workflows. Then independent infosec and privacy authorities evaluate physical proof. Only a real release owner can consider release; the software gate never grants it itself.

## 4. Provider/tool blocker

Connected Render workspace `My Workspace` returned **no services and no Postgres instances** at inspection. Available Render connector actions can create public `web` services and managed Render Postgres, but not private `pserv` services or an operator-controlled clientcert-enforcing PostgreSQL. Using a public web service or Render's `sslmode=require` database as a substitute would violate the approved ABC zero-trust boundary.

**Engineering disposition:** `P04=IN_PROGRESS`, `PR=DRAFT`, `PRODUCT_RELEASE=BLOCKED`, `ACTUAL_PROVIDER_MTLS=NOT_DEPLOYED`, `REAL_SIGNOFFS=NOT_RECEIVED`. All successful CI evidence (when present) must be linked to the exact SHA of this PR; never reuse a green result from an earlier commit.
