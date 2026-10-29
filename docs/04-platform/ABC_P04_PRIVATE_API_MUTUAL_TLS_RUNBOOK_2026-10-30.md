# ABC Phase04 — Private API mTLS hardening and controlled deployment gate

**Status:** DRAFT / SOURCE-CONTROLLED / synthetic-only.  
**Change:** stacked draft PR #42 over #41 → #40 → #39 → #38 → #36.  
**Out of scope:** AI model inference APIs, billable LLM/image API provisioning, real customer records or live customer access.

## 1. Discovered and corrected risk

The previous private `staging_api.py` used `ThreadingHTTPServer` with **plaintext HTTP** on `0.0.0.0`. Render private network reduces external reachability but is a **workspace/region network boundary, not authenticated transport**. An unauthorized peer inside that boundary could otherwise observe OIDC bearer tokens or make traffic assertions not backed by a client certificate.

**Correction:** no plaintext listener is constructed. `create_private_api_server` mandates `ABC_API_TRANSPORT=MTLS_TLS13`, an externally provided server certificate/private key/trust CA, and an exact list of permitted caller URI SANs. The server requires the client to present an X.509 certificate trusted by its CA. Each accepted connection must also contain **exactly one allowed URI SAN** (for example `spiffe://abc.internal/gateway/<registered-consumer>`); CN, DNS SAN, wildcard and multiple conflicting URI SANs are not substitutes. Rejected clients are disconnected before parsing HTTP.

This does **not** replace OIDC authentication and tenant/branch permissions in ENG-01/14. They remain independent gates, as do server-side PostgreSQL `hostssl` client-certificate enforcement, RLS, decision provenance, and signed professional approval.

## 2. Proposed private topology

```
  In-salon client + specialist display
               |
    [approved application edge / gateway]
    OIDC verification + issued workload client cert
               |
        HTTPS TLS1.3 mutual auth
               |
     [ABC Phase04 private API: pserv]
        pinned upstream client URI SAN
        ENG01 broker / ENG14 SQL policy
               |
     PostgreSQL over separately owned private channel
      server-controlled cert validation + NOINHERIT login
               |
       ENG03 durable queue/worker
               |
    3 distinct TLS1.3 mTLS connections
          /        |        \
       ENG04     ENG05     ENG06
      private    private    private
      pserv      pserv      pserv
```

- The HTTPS private API candidate is at `infra/render/private_api.staging.template.yaml`; all sensitive configuration is `sync:false`, the service is `type:pserv`, and `autoDeployTrigger=off`.
- The engines' candidate manifest remains `infra/render/private_engine_services.staging.template.yaml`.
- Both manifests are **nonactive plans**; no Render resource exists, no actual CA has been issued, and no database ingress can be asserted secure in the linked workspace.
- A normal Render-managed PostgreSQL internal URL **does not** implement the target `sslmode=verify-full` physical server/client certificate assurance. Do not substitute it for operator-managed PostgreSQL or a separately assessed equivalent.

## 3. External operator prerequisites

1. Select an approved private infrastructure/provider account and region; confirm costs and quotas **before** any provision. This phase needs **no paid AI API**; cloud services and managed PKI can nonetheless have hosting costs.
2. Use an independent PKI authority with key material held outside GitHub, CI artifact archives, ChatGPT output and container images. Issue a dedicated server certificate for the API containing its exact private Render hostname in DNS SAN; issue a **different** dedicated client certificate for its approved gateway with a unique URI SAN. Rotate and revoke both with tested overlap rules. No wildcard SAN or shared key pair.
3. Enforce the API's private-only service type by provider configuration, not `ABC_NETWORK_BOUNDARY` environment text. Capture service ID/region, private hostname/port, public-URL absence and security logs as *external evidence*.
4. Enroll a dedicated PostgreSQL physical LOGIN and client certificate. Verify server `pg_hba.conf`, fixed DN mapping, `sslmode=verify-full`, `pg_stat_ssl` certificate identity, revocation, RLS FORCE and rollback with the 17 immutable migrations. Any reuse of the synthetic shared `abc_app` credential for a managed tenant is forbidden.
5. Bind ENG03 to ENG04/05/06 with unique workload identities and external RS256/JWKS issuer; independently verify source service audience, certificate fingerprint, consumer ID and network reachability. Implement a **distributed replay ledger** before multi-instance scaling; per-process replay detection alone is insufficient.
6. Obtain signed and independently verified professional S1–S3 service SOP, contraindication evidence, qualified reviewer identity, privacy/consent/DSR review and security decision. No model or token string may self-authorize a treatment or production rollout.

## 4. Live private API smoke (after provisioning only)

Execute `python -m abc_foundation.staging_mtls_smoke` **inside the real approved private network**, with the following externally injected environment variables:

| Variable | Meaning |
| --- | --- |
| `ABC_ENV=STAGING_PRIVATE` | Synthetic-only staging isolation |
| `ABC_STAGING_PURPOSE=SYNTHETIC_NO_CLIENT_DATA` | No client/media payload |
| `ABC_NETWORK_BOUNDARY=RENDER_PRIVATE_SERVICE` | Defense-in-depth declaration, not provider proof |
| `ABC_PRIVATE_API_MTLS_URL` | Exact `https://abc-p04-private-api-synthetic-<provider-suffix>:10000`, matching server DNS SAN |
| `ABC_PROBE_CLIENT_CERT_FILE` | External client certificate chain path |
| `ABC_PROBE_CLIENT_KEY_FILE` | Restricted external private key path |
| `ABC_PROBE_ROOT_CA_FILE` | Pinned trusted private CA path |

This probe requires live TLS verification and only performs `GET /healthz` (200 with expected synthetic capability) and unauthenticated `POST /v1/consultations` (401). It sends **no bearer token, real customer data, image or procedure instructions**. Success produces a machine-readable `REAL_PRIVATE_API_MTLS_PROBE_NOT_RELEASE` result with `release_approved=false`.

The former `staging_smoke.py` is a **legacy plaintext network probe** and MUST NOT be presented as live managed-mTLS proof. The mTLS probe is the only approved prospective private API test for this workstream.

## 5. Release gates and evidence

| Gate | Physical source evidence | Status |
| --- | --- | --- |
| Physical CA/JWKS issuance | Issuer records, public CA chain, revocation and renewal drill | NOT PROVIDED |
| PostgreSQL server/client mutual TLS | Operator-controlled server config and live authenticated connection evidence | NOT DEPLOYED |
| Managed ENG01/14 login cutover | No shared runtime login, replay/CAS + RLS tenant proofs | CI-TESTED, LIVE BLOCKED |
| Private API TLS1.3 client SAN | Client/server cert chain and live connection rejection from a private peer | CODE/CI-TESTED, LIVE BLOCKED |
| Three private ENG04/05/06 | 3 independent live service IDs, no public ingress, actual routed E2E and failure drills | NOT DEPLOYED |
| Distributed replay protection | Shared durable jti registry across all replicas | NOT IMPLEMENTED |
| Professional / privacy governance | Independently issued, reviewed signed authorization and consent | NOT APPROVED |
| Operational resilience | PITR, tested backup restore, egress restrictions, logging, alarms, pen test | NOT APPROVED |

**Decision:** `PHASE04=IN_PROGRESS`; `PR=DRAFT`; `MAIN=UNCHANGED`; `LIVE_DEPLOYMENT=BLOCKED`; `CUSTOMER_RELEASE=BLOCKED`. Passing a disposable CI PKI test is not proof that externally managed certificates or private Render services exist.
