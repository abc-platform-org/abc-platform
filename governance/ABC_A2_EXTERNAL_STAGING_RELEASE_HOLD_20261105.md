# ABC A2 — private staging independent acceptance: hard release hold
Date: 2026-11-05
Decision: PREDEPLOYMENT REVIEW PACKET PREPARED. REAL MANAGED STAGING NOT DEPLOYED. A2 OPEN. ENG-06 RELEASE BLOCKED.
Branch: implementation/w1-eng05-external-approval-gate-20261101, existing draft PR #78; do not merge.

## Verified facts and blockers

The connected Render workspace tea-dbhglamc6qcc73fcjer0 was queried read-only. It lists no services and no PostgreSQL instances. This is not a universal statement about all external cloud accounts. GitHub PR #78 contains no independent review submissions at inspection time.

Authoritative governance/phase04_infrastructure_selection.v1.json has billing_authorized=false and deployment_authorized=false, without a numeric spend cap or approved provider. Issue #63 requires explicit owner/operator/provider/cost approval before resource creation. Issues #37 and #43 require real private-network and PostgreSQL clientcert authentication. Issue #79 requires independently credentialed professional source and safety approval. ADR-ENG-003/004 are not ratified. None of these is satisfied by CI.

Render ordinary managed PostgreSQL with sslmode=require does not meet the currently selected server-enforced clientcert=verify-full plus pinned client verify-full requirement. Do NOT create a public Render Web Service or treat ephemeral CI CA and worker identity as managed PKI.

## Physical implementation criteria

1. Seven independently authenticated engine principals: ENG-01, ENG-02, ENG-03, ENG-04, ENG-05, ENG-06, ENG-14. Each requires exact private provider resource ID, unique managed SPIFFE (or equivalent) principal, operator-issued key/cert, independently verified OIDC/JWKS and token/cert rotation and revocation. No shared static worker passwords.
2. Dedicated PostgreSQL 16+ in private network with pg_hba hostssl and server enforced clientcert=verify-full, client-side sslmode=verify-full and pinned root CA, seven dedicated LOGIN NOINHERIT NOBYPASSRLS bindings, FORCE RLS, no password-only bypass, server-derived TLS peer audits. Physical backup, PITR and isolated restore proof.
3. Private network deny-by-default with *both* outsider DNS and direct private-IP negative tests; no public engine or DB ports; restricted egress. Provider route table and network ACL exports inspected directly by independent security reviewer.
4. ENG-14 consent, human qualification, session state version, audience, JTI replay and source-provenance gates enforced at the actual protected DB/engine boundary. Revocation and concurrency tests. No automatic ENG05->ENG06 dispatch and no customer media.
5. Provider-hosted crash/restart, PG restart, lease fencing, retry/DLQ, no duplicate effects, measured RPO/RTO, alerts, on-call and rollback.
6. Independently accountable Security and SRE reviews, operator signoff, owner authorization, and independent qualified specialist review with real credentials, rights, scope and effective dates. A signed PR comment or CI status does not by itself prove those qualifications or provider truth.

## Mandatory external evidence slots

An operator must supply independent raw provider exports, private-network probes, managed issuer/cert metadata and log SHA256s for all keys below. Each receipt must identify actual resource IDs, exact deployed commit, tested region, provider, timestamps and trusted third-party cross-check.

- provider_resources
- private_ingress_denials
- network_acl_and_egress
- managed_workload_issuer
- certificate_rotation_and_revocation
- postgres_clientcert_negatives
- human_oidc_attestation
- eng14_consent_race
- durable_recovery_and_replay
- restore_and_rollback
- monitoring_and_alerting

All evidence and reviewer trust anchors must be kept in an operator-controlled private location *outside* the repository; never commit credentials, real customer records, trust root private keys or protected log payloads. Current GitHub actions do not obtain real evidence or external approval.

## Reviewer signing contract (integrity, not identity issuance)

The script scripts/a2_external_staging_acceptance.py verifies an external packet against operator-held trust roots, external artifact SHA256 and five independent Ed25519 detached signatures. Required receipt roles are owner, operator, security, sre and specialist, all different identities. Signed decision is APPROVE_PRIVATE_STAGING_EVIDENCE_ONLY for exact full Git commit, packet SHA256, issued/expiry times. It is not an authorization for ENG-06 release.

Example, after an independently authorized operator actually provisions private staging and obtains real evidence:

python scripts/a2_external_staging_acceptance.py --packet /operator/packet.json --trust /operator/trusted-reviewers.json --evidence-dir /operator/provider-evidence --head FULL_40_HEX_GIT_SHA

Packet schema abc.a2.external-staging-acceptance.v1. Trust registry schema abc.a2.operator-pinned-reviewer-keys.v1. Canonical packet digest uses sorted compact ASCII JSON excluding approvals. Detached receipt signature covers all receipt fields except signature_b64. Reviewer public keys must be externally pinned and human qualifications checked independently. A successful integrity check explicitly returns provider_actuality=REQUIRES_SEPARATE_LIVE_PROVIDER_CROSS_CHECK, a2_operational_closed=false and eng06_release_approved=false.

The 16 offline regression tests use invented reviewer keys, simulated provider records and fictional IDs: they assert that missing/fake approval, modified logs, bad PG clientcert, public network, unsafe release, replay risk, reused identity or incorrect SHA cannot pass. They are not staging acceptance results.

## Controlled commissioning steps

1. Owner and operator select authorized private provider/region/plans, numeric spend ceiling and responsible billing/rollback parties; no chargeable resource before approval in issue #63.
2. Security ratifies the design and ADR-ENG-003/004. SRE reviews the disaster recovery and monitoring plan. External CA/OIDC provider and independently managed secrets custody are confirmed.
3. Authorized operator provisions the seven private workloads, external clientcert-verified PG and private ACLs; extracts actual provider IDs and proves no public endpoints.
4. Run provider-network mTLS, JWT and PG negative probes, certificate rotation, consent/revocation/replay, full synthetic engine handoff, crash/restart, PITR and rollback. Record measured p95/p99 and RPO/RTO against preapproved targets.
5. Separate Security reviewer verifies provider evidence independently and signs exact commit and SHA. Separate SRE reviewer does independent restore/monitoring/fault acceptance. Independently qualified specialist signs only their professional scope; never forge signature.
6. Owner and governance consider A2 closure in a *different* decision after all external evidence. Even approved private staging does not authorize customer or ENG-06 operational release.

Current hard status: G06_CI_SYNTHETIC=PASS (Actions #42092012678). MANAGED_STAGING=UNVERIFIED; EXTERNAL_SECURITY_SRE_SPECIALIST_APPROVAL=ABSENT; A2=OPEN; ENG06_RELEASE=BLOCKED. No paid provider resources or real secrets were created by this packet.
