# ABC — Managed PKI, Database Identity and Private ENG04–06 Rollout Runbook

**Engineering state:** source/CI candidate; **NO PROVIDER CONFIGURATION OR LIVE DEPLOYMENT**.  
**Release:** BLOCKED. No actual service identity, private CA, tenant credentials, client data or paid resource has been created.

## 0. Provider compatibility decision

Render Private Services (`type:pserv`) provide private ingress to peer services in the same region/workspace and no public `onrender.com` URL. They do **not** by themselves authenticate service identity: our TLS 1.3 + RS256/JWKS bound workload identity must remain enabled.

Render-managed PostgreSQL internal connection uses a self-signed TLS certificate and `sslmode=require`. Its published documentation explicitly says internal `sslmode=verify-ca` and `verify-full` are unsupported. Therefore the **existing `managed_db_identity.py` verify-full + client-cert expectation cannot be considered achieved by creating an ordinary managed Render Postgres instance**.

**Production architecture selection:** independent, operator-controlled PostgreSQL 16+ inside an authenticated private network with `hostssl`, a dedicated CA and `clientcert=verify-full`, authenticated dedicated LOGIN + RLS and documented backup/restore, OR a separately security-reviewed mTLS-terminating gateway that provides equivalent cryptographic DB login binding and a hard non-bypassable protected DB channel. Neither alternative is implemented/deployed today. A normal `sslmode=require` connection does NOT meet the current target assurance.

## 1. Keys / trust / roles — external operator responsibility

Required cryptographic material is generated in the provider's dedicated secrets/PKI system, **not in GitHub, ChatGPT, Docker build, application logs or a migration**.

- Dedicated offline/managed root CA; short-lived issuing CA for internal services; distinct identity for ENG-01, ENG-03, ENG-04, ENG-05, ENG-06 and every database-capable consumer; no shared key.
- Exact URI SAN: `spiffe://abc.internal/eng03/<consumer>` for the pipeline caller and corresponding per-engine subject, with an independently pinned external HTTPS JWT issuer; token subject, engine ID, consumer ID and audience must agree with certificate identity.
- Each client JWT: RS256 with pinned issuer/audience, external JWKS `kid`, short validity (current runtime cap 120 seconds), certificate SHA-256 thumbprint confirmation and unique `jti`. **JWT replay detection across independent service instances is not yet implemented**; durable bounded replay tracking, expiration, clock skew and token renewal must be approved before production.
- Separate mTLS server cert per ENG-04/05/06 containing the exact Render private service hostname as DNS SAN, signed by a private CA; client trust roots injected via an approved secrets mount. Public CA/browser TLS does not substitute for mTLS client identity.
- Two-phase rotation: publish new trust anchors, rotate keys/certs with bounded overlap, revoke and verify old credentials fail closed, then remove old CA/JWKS; rehearse issuer outage, lost credentials, expired cert and compromised engine role scenarios.

## 2. PostgreSQL managed-mode cutover

Migration 0017 adds `abc.eng14_tenant_workload_mode`. When `managed_required=true`, **all** ENG01 creation, ENG14 pause broker and SQL state-trigger checks share `abc.eng14_workload_allowed(tenant)`. The function checks the physical immutable `session_user`, active tenant-scoped `eng01_api_login_bindings`, and server-derived `pg_stat_ssl` TLSv1.3, cert DN, issuer DN and serial against administrator-pinned values. The legacy direct `abc_app` login is explicitly denied for that tenant. Raw `UPDATE(updated_at)` remains prohibited by an invoker-role trigger.

**Never set `managed_required=true` until the following are proven:**

1. The PostgreSQL server (not just the client) requires verified client certificates by `hostssl ... clientcert=verify-full` or equivalent and a fixed `pg_ident` mapping. Neither a custom GUC nor SSL encryption alone proves certificate trust.
2. Unique app logins exist as `LOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS`; role `abc_app` can be adopted only through an operator-granted `SET ROLE`, not login inheritance. Grant only current tenant/consumer binding.
3. RLS remains FORCE-enabled across all relevant records, revocation and tenant separation pass negative tests, all privileged function owners/search paths have independent security review.
4. The complete `ENG01.create`, `ENG01.pause`, legacy checkpoint and ENG14 DB trigger paths pass with **actual** identity-authenticated private database connections; a synthetic unit test is insufficient.
5. A staged, backed-up migration with checksum journal and tested rollback is complete; connection-pool identity reset/transaction reuse are explicitly tested.
6. Remove direct shared login usage for all production/sensitive traffic, rotate any old shared credential and verify former credentials have zero privileged paths.
7. Only an authorized security operator writes an activation row with nonempty audit actor/timestamp; a request body, model, tenant manager or UI may never set this switch.

## 3. Private Render ENG04/05/06

The non-active template `infra/render/private_engine_services.staging.template.yaml` defines three independent `pserv` containers. They must be provisioned in a **confirmed workspace and one region**, with operator-approved cost and externally injected secret paths; automatic deployment remains off.

- Private DNS for Render uses provider-issued **single-label hostnames**, typically derived from service name plus a suffix. The mTLS client now permits only a hostname derived from the intended `ENG-04/05/06` name (or an exact engine-scoped `.internal` alias), with `server_name` identical to the host and the server certificate DNS SAN matching it. Public hostnames always fail.
- Require `ABC_ENV=STAGING_PRIVATE`, `ABC_NETWORK_BOUNDARY=RENDER_PRIVATE_SERVICE`, `ABC_RENDER_SERVICE_KIND=PRIVATE`, `ABC_ENGINE_SYNTHETIC_ONLY=true`; these are defense-in-depth declarations, **not proof of the hosting account's private network**.
- Run one nonroot container for each target, independent secrets/identities, controls for egress and timeouts. The three current processes on one local host are not a security boundary.
- The PG pipeline currently defaults to local isolated child processes. Network mode must be selected explicitly by an authenticated `ManagedMTLSEngineClient` and reviewed owner; no implicit proxy to a public endpoint or insecure fallback.
- Execute private-network smoke/E2E with real CA/JWKS and certificate rotation/revocation, wrong issuer/kid/consumer/cert SAN and endpoint mismatch, replay, crash recovery and lease/ACK transaction integrity.
- Verify no public service URI, no internet-accessible port, and no unexpected cross-tenant/private workspace traffic from a peer service.

## 4. Critical remaining assurance gaps

| Gate | Evidence required | Present state |
| --- | --- | --- |
| CA/issuer issued | CA rotation report, signed workload cert chains, managed token broker | MISSING |
| Physical database TLS | Server hostssl + trusted client CA + certificate CN mapping, actual DB peer audit | MISSING |
| Persistent token replay protection | Per-issuer/consumer/jti bounded replay ledger and multi-node tests | MISSING |
| Production credential isolation | No shared `abc_app` login, distinct roles/secrets, successful managed-mode cutover | MISSING |
| Private Render instances | Three service IDs/regions/ports, no public DNS, managed secret mount, live health evidence | MISSING |
| Safety policy approvals | Named verified qualified specialists, signed SOP and consent/law/retention approvals | MISSING |
| Product operations | Observability, alerts, rate limits, backup/restore, load, pentest and incident drills | MISSING |

## 5. Exit and release rule

Code/CI acceptance proves only **synthetic engineering correctness**. A product release requires an **independent physical-provider evidence bundle** with certificates/issuer *public metadata only* (never private keys), active Render service IDs, server-side DB authentication logs/config, reproducible negative tests, and signed specialist/legal/ops approvals.

Until then: `PHASE04=IN_PROGRESS`, `MANAGED_IDENTITY=NOT_PROVISIONED`, `PROFESSIONAL_POLICY=NOT_SIGNED`, `PRIVATE_ENGINE_SERVICES=NOT_DEPLOYED`, `RELEASE=BLOCKED`.
