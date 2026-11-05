# ADR-ENG-005 — Managed workload identity, mTLS/JWT and private authorization for ABC

**Decision status:** TECHNICAL DESIGN CANDIDATE FINALIZED FOR INDEPENDENT REVIEW — NOT RATIFIED.
**Date:** 2026-11-05. **Dependency:** ADR-ENG-003 canonical ownership; ADR-ENG-004 v2-to-19 read-only adapters.
**Change:** The prior 2026-10-31 file ADR_ENG_004_WORKLOAD_IDENTITY_AND_TRUST_BOUNDARIES_W0_2026-10-31.md incorrectly reused the ADR-ENG-004 identifier. That old file is a historical security annex, NOT the canonical ADR-ENG-004. ADR-ENG-004 is the v2 adapter decision. Use ADR-ENG-005 for workload identity thereafter. Renumbering is a review candidate and has NOT been formally ratified.

## Decision proposed for independent ratification
1. Nineteen logical capability owners do NOT imply nineteen public services. ENG-01 owns orchestration, ENG-14 policy; seven predeployment principals ENG-01/02/03/04/05/06/14 are independently scoped. Separate private workload credentials and distinct DB roles are required; synthetic login fixtures cannot be called managed principals.
2. A managed workload identity requires external CA/issuer, operator-controlled key lifecycle, unique certificate identity and JWT bound to actual TLS peer, exact audience and route, short lifetime <=120s, unique canonical UUID4 JTI, issuer/subject pinning, no token-selected key URLs/JWKS, and independently verified revocation. SSL encryption by itself is not peer identity.
3. Canonical private ingress is ENG-03->ENG-04, ENG-04->ENG-05, ENG-05->ENG-06 ONLY. No ENG-03->ENG-05 or ENG-03->ENG-06 shortcut. All handoffs retain immutable source identity, tenant, branch, session, state version, consumer, artifact hashes and independent ENG-14 decision reference. Caller-supplied ALLOW or policy proof string is never authority.
4. Managed private services MUST refuse to start unless an externally supplied atomic/durable replay-admission implementation is wired. Existing process-local _LocalReplayWindow is CI-only. A callback shape is a protection hook, not proof of a genuine managed issuer, durable PG transaction or independent professional gate. No automatic action is authorized by successful JWT verification alone.
5. Server-enforced PostgreSQL hostssl with clientcert=verify-full and pinned client-side sslmode=verify-full; dedicated physical LOGIN NOINHERIT NOBYPASSRLS and separate NOLOGIN permission groups; FORCE RLS on protected tables, operator-only grants and direct negative privilege tests. Managed proof requires real pg_stat_ssl, session_user, expired/revoked cert and stolen-password checks. The legacy synthetic abc_app login and writable GUC alone are not professional authority.
6. ENG-14 denies all unapproved S1–S3 transitions; only bounded S0 CREATED->PAUSED synthetic checkpoint may be allowed by independent database broker with CAS and specialist membership. Human qualification, purpose-specific consent, provenance, live state and policy must be re-evaluated at claim and ACK. ENG-05->ENG-06 is review-only, ENG-06->ENG-07/customer release remains prohibited.
7. A candidate staging template with private DNS is NOT actual network isolation. Network policy must be default-deny, no public ingress/PG, restricted egress, direct-IP and DNS negative probes, no public fallback, no customer data, and operator-held secrets. External managed CA, IdP, actual provider service identities, CERT revocation/rotation and backups must be verified by independent Security/SRE.

## Contract reconciliation and known open blockers
- Existing runtime peer URI format is spiffe://abc.internal/engXX/{consumer}, while W0 candidate registry proposes spiffe://abc.internal/staging/eng-XX. These are NOT compatible. No operational identity enrollment until a single explicit versioned SPIFFE URI policy (service identity vs tenant/consumer subprincipal) and certificate issuance mapping are chosen and reviewed. The current runtime keeps synthetic URI compatibility for regression only.
- Real distributed replay and ENG-14 consent/state admission are NOT automatically wired by the private staging entrypoint. The entrypoint now DENIES startup without a durable replay-admission callback, and no approved external provider implementation is supplied. Never substitute a lambda or ephemeral cache for the managed implementation.
- ENG-02 pre-capture persistence remains unavailable (returns fail-closed) until consent and media lifetime are independently verified.
- A1 legacy adapter projections remain read-only/quarantined. v1/v2 contracts are unchanged. Historical ENG19 review transport is not canonical ENG-19 automation.
- Owner has ordered independent staging provisioning ON HOLD until provider and cost approval (#63). No public/paid resource, managed CA, production specialist credential or external database is created by this ADR.

## Review-gate evidence required (no self-approval)
Architecture owner: identify 19 owners, six v2 adapters, 17-stage graph and ADR-004/005 renumbering decision; review final SHA and frozen contract hashes.
Security reviewer: source and DB grants, private mesh TLS chain, JWKS trust, signed JWT and replay/consent races, token/cert rotation, negative revoked/forged privileges and SPIFFE naming resolution; signed disposition on exact SHA.
SRE reviewer: private deployed resource IDs, network isolation, RPO/RTO/restore, nonroot deployment, observability, rotation and rollback; independent signed disposition.
Qualified salon professional: externally verified qualification, source rights, service SOP, consent and risk boundaries; separate signed authorization before any real ENG-06 output.
Owner: approve provider/region/billing/operator budget separately before any deployment. Approval of *design* never authorizes infrastructure spend or release.

## Negative test evidence scope
- test_private_engine_mtls.py: actual disposable TLS1.3 peer authentication, JWT issuer/audience/cnf/JTI/hostile key-header, routing and no-public-mode tests.
- test_a2_adr003_004_pg_roles.py: actual disposable PostgreSQL16 privilege and FORCE RLS negative SQL, denied direct role reads/legacy unbound broker.
- test_eng14_transition_gate.py and test_a2_g05_atomic_authorization.py: source-locked ENG-14 policy, synthetic consent/version/revocation and durable replay checks.
- G04-C container mTLS and G06 restart CI: actual local disposable containers/PG restart ONLY; not external managed staging.

**Ratification ledger:** ADR-ENG-003 = DESIGN CANDIDATE / REVIEW PENDING. ADR-ENG-004 = ADAPTER DESIGN CANDIDATE / REVIEW PENDING. ADR-ENG-005 = IDENTITY DESIGN CANDIDATE / REVIEW PENDING. Security = UNSIGNED; SRE = UNSIGNED; Specialist = UNSIGNED; A2 = OPEN; ENG-06 RELEASE = BLOCKED.
