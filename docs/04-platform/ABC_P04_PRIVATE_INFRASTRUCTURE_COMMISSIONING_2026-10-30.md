# ABC P04 — Private Infrastructure Commissioning Candidate (NO DEPLOY)

**Date:** 2026-10-30. **Decision:** choose verified private network and physical certificate identity before creating paid resources. **Not approved to spend or deploy.**  
**Repository:** stacked on PR #50. **Code CI ≠ live infrastructure attestation.**

## Provider viability finding, verified from official documentation

The Render API currently connected to this conversation supports `create_web_service` (public-facing) and `create_postgres`, but **not** `create_private_service`. Therefore no public web service was substituted and no paid resource was provisioned.

The Render Dashboard/Blueprint **does** support private services (`type: pserv`). However, the official Render Postgres documentation states that **internal Render Postgres TLS does not support `sslmode=verify-full` or `verify-ca`**. ABC's approved architecture requires external issuer-controlled client certificate authentication at PostgreSQL (server `hostssl ... clientcert=verify-full`, client `sslmode=verify-full` and pinned server CA) and physical-workload identity recorded in `pg_stat_ssl`. **A standard Render-managed Postgres instance must NOT be represented as meeting this requirement.** Reference: <https://render.com/docs/postgresql-creating-connecting>, <https://render.com/docs/private-services>, <https://render.com/docs/blueprint-spec>.

## Preferred candidate, pending funded architecture review

- **Compute:** 4 independently managed private Render services (API, ENG04, ENG05, ENG06) and one background worker ENG03. Region candidate Frankfurt, no public hostname, manual deploy only, isolated image revision/identity/certificate per service.
- **Database:** externally operator-controlled PostgreSQL 16 on a **private network reachable from compute**, enforcing TLS1.3, physical client certificate, server-cert hostname verification, RLS, single-use JTI replay, migrations 0001–0018, audit backups and independently tested restore.
- **Identity:** dedicated external CA + workload JWKS/IdP, pinned SAN URI, distinct service roles, key-vault secret mounts, revocation and rotation procedures. No in-repository private keys, human/password fallbacks or fabricated signed SOP.
- **Privacy:** synthetic-only until consent, professional review, regulatory checks, retention/erasure and pilot release are independently approved.
- **Network feasibility:** private service on Render **does not alone guarantee a private route to an externally hosted Postgres**. An actual supported private link, privately routed tunnel or common private cloud network **must** be independently verified. If unavailable or financially unsuitable, move the five private services into the same operator-controlled network as PostgreSQL instead of weakening database authentication.

### Files to review, not deploy

- `governance/phase04_infrastructure_selection.v1.json`: specific provider fit, target five-service topology, evidence deficits and unapproved spending.
- `infra/render/p04_private_services.nonactive.candidate.yaml`: **nonactive** four-pserv/one-worker Blueprint sample, no public service, no Render database, no auto-deploy, no actual secrets or host credentials. It currently uses only the already-tested legacy synthetic v1 listeners; it **does not claim to deploy v2 inference**.
- `scripts/validate_p04_provider_fit.py`: CI refusal of public substitutions, unsigned approval/budget, unreviewed DB, credential injection, altered branch or auto-deploy.
- `scripts/attest_p04_external_postgres.py`: read-only operator-side verifier of PostgreSQL16 physical `session_user`, TLS1.3, client certificate DN/issuer/serial and forced RLS. Requires external mounted secret material and does not print the DSN or private key.
- `governance/phase04_readiness.v1.json`: the ten independent closure gates remain OPEN.

### Pre-provision approval (necessary; not a blanket permission to spend)

A real operator/owner must select and record: monthly USD spending cap; region and location/data residency; compute plan; external PG provider and proof of client-cert control; **private routing path between compute and database**; CA/IdP provider; secret storage; qualified security/DBA contact; on-call/rollback owner; backup/PITR plan and automated shutdown budget guard. Neither the Render connector nor this draft can mint independent professional signatures or attest a private network that is not provisioned.

Render publicly lists starter-class compute at **USD 7 per service/month** and Hobby workspace at **USD 0 plus compute**, so *five minimal services* would have a **USD 35/month compute-only illustrative subtotal** if those plans are available. This **excludes** externally managed PG, private networking/link, PKI, backups, egress, higher-instance CPU/RAM, tax, and any workspace upgrades; it is **not** a quoted or approved monthly budget. Source: <https://render.com/pricing> (checked 2026-10-30). Evaluate provider availability and projected total **before** creating any resource.

## Live acceptance procedure (requires independently approved access)

1. Provision private network, external CA and Postgres16. Prove exact client/server TLS1.3, `verify-full`, physical LOGIN, role separation, forced RLS and non-public reachability; capture redacted evidence IDs.
2. Apply checksum-validated database migrations under a separate operator `abc_staging_migrator` identity, never an application credential. Validate real replay ledger in 2+ instances and restore from an actual backup.
3. Provision five separate private services with controlled secret mounts and immutable image SHA. Confirm no internet inbound route, exact SAN and audience; test peer identity rotation and revocation.
4. Upgrade the v2 local-only listener into an **independently reviewed private deployment adapter**, with real ENG01 membership/consent authority and separate ENG14 policy verification. Do not set an environment variable to bypass that protection.
5. Execute synthetic E2E + wrong tenant/client certificate/JTI replay/consent withdrawal/worker crash/rolling deploy/observability/SLO tests. Then complete independently signed P04-01..10 and G01..G10 reviews.
6. Approve P04 closure and customer rollout independently; professional and privacy approval are **not** derived from code CI or existence of infrastructure.

### Status

**Actual Render workspace:** no services or Postgres presently found.  
**Provisioning:** not executed; neither approved monthly cost nor required private service endpoint is available through connected Render tools.  
**Phase04:** IN_PROGRESS; **0/10 P04 independent gates closed**. Product release BLOCKED.
