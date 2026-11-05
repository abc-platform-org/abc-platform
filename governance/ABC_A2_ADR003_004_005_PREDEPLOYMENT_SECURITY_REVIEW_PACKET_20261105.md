# ABC A2 — ADR-ENG-003 / ADR-ENG-004 / proposed ADR-ENG-005 Predeployment Review Packet

**Date:** 2026-11-05. **Status:** TECHNICAL DESIGN REVIEW CANDIDATE; SECURITY / SRE / PROFESSIONAL / ARCHITECTURE RATIFICATION **NOT RECEIVED**.
**Repository:** saleheebrahimi2029-hub/abc-platform, existing PR #78, branch implementation/w1-eng05-external-approval-gate-20261101. Reviewers must use the FINAL head SHA shown by GitHub after CI, not any earlier test SHA.
**Owner decision:** No independently hosted staging provisioned and no cost authorized; issue #63 holds all deployment. Issues #84/#85 request independent Security/SRE review; #79 qualified specialist. A2 OPEN and ENG-06 RELEASE BLOCKED.

## 1. ADR identity, semantic ownership and audit reconciliation

| Identifier | Source of truth | Scope | Current ratification |
|---|---|---|---|
| ADR-ENG-003 | docs/04-platform/ADR_ENG_003_CANONICAL_19_ENGINE_OWNERSHIP_AND_WORKFLOW_2026-10-30.md | 19 logical owner responsibilities and 17 ordered data-plane stages | UNSIGNED |
| ADR-ENG-004 | docs/04-platform/ADR_ENG_004_V2_TO_19_ADAPTER_COMPATIBILITY_2026-10-30.md | Six read-only v2-to-v3 capability projections; no semantic alias or dispatch | UNSIGNED |
| Proposed ADR-ENG-005 | docs/04-platform/ADR_ENG_005_MANAGED_WORKLOAD_IDENTITY_AND_TRUST_BOUNDARIES_2026-11-05.md | managed workload identity, mTLS/JWT, PostgreSQL and ENG14 private trust boundaries | UNSIGNED |

Historical file ADR_ENG_004_WORKLOAD_IDENTITY_AND_TRUST_BOUNDARIES_W0_2026-10-31.md was *misnumbered*, is preserved and explicitly flagged as an old security annex. Renumbering and new ADR-005 assignment require independent architecture owner ratification; no approved numbering is fabricated. Machine registry source_adr now includes all three identifiers but still signals unapproved.

## 2. Enforced program scope

- ENG-01 orchestration; ENG-14 independent deny-first policy authority; ENG-02 consent before capture (currently fail closed); ENG-03 evidence; ENG-04 analysis; ENG-05 knowledge; ENG-06 review-only decisions. ENG-07 to ENG-19 are not automatically executable or released by this packet.
- Active review-only synthetic TLS edges must follow ENG-03 → ENG-04 → ENG-05 → ENG-06. Private Blueprint caller IDs corrected; no ENG-03 → ENG-05/06 shortcuts.
- Existing frozen v1/v2 schemas, CI migrations 0001–0034, six quarantined read-only A1 compatibility adapters and customer release guard remain unchanged. No paid AI inference calls.

## 3. Implementation and negative evidence supplied

| Boundary | Security property | Verification | Residual blocker |
|---|---|---|---|
| JWT signature/subject/cnf | Pinned RS256 issuer/JWKS, exact single audience, header key-location denial, canonical UUID4 JTI, cert SHA binding | test_private_engine_mtls.py / G04-C TLS loopback tests | Managed issuer, cert issuance/revocation and full IdP integration unverified |
| TLS transport | TLS1.3 mutual certificates, client SAN and server hostname verification, private-only policy, no HTTP/public fallback | test_private_engine_mtls.py; G04-C disposable Docker network probes | Real provider network and provider-issued certificate trust unverified |
| Replay in managed mesh | Runtime launcher remains fail-closed; local-only PG atomic adapter holds current ENG14 consent/state and one-shot JTI locks through synthetic dispatch | test_a2_private_spiffe_pg_multinstance.py / 16 PG+TLS cases / 8 processes and 3 listeners; test_private_engine_mtls.py | External operator-managed PostgreSQL clientcert binding, workload issuer and actual hosted adapter not implemented/attested |
| SQL role separation | ENG04/ENG05 distinct NOLOGIN groups; ENG06 review-group lease; no legacy G05 unbound function access; protected tables FORCE RLS | test_a2_adr003_004_pg_roles.py, 10 real disposable PostgreSQL16 tests | Seven real managed workload logins, external physical PostgreSQL client-cert verification and pre-approved grants unprovisioned |
| ENG-14 state and policy | 101 state edges blocked; only approved bounded synthetic S0 CREATED→PAUSED; G05 certificate-grant, consent, version, Replay checked in disposable DB | test_eng14_transition_gate.py, test_a2_g05_atomic_authorization.py | Human OIDC attestation, all operational S1–S3 and professional qualification authorizations unapproved |
| Provenance/outbox | Synthetic ENG05→06 outputs are BLOCKED_PENDING_AUTHORITY; ENG06 ACK is review only; ENG07/real customer dispatch forbidden | G06 fault and PG restart tests; review source/receipt tests | No external source legal/professional signoff |

**SPIFFE scheme reconciled in source:** `spiffe://abc.internal/staging/eng-XX` is now the canonical per-engine TLS SAN and JWT `sub`, matching W0's seven-engine registry. Signed `consumer_id` is a separate scope. Legacy per-consumer SPIFFE is rejected in negative mTLS tests. The external PKI operator's ownership of this trust domain, real issuer setup and independent architecture ratification remain UNVERIFIED; source consistency is NOT a managed identity attestation.

**Mandatory implementation caution:** `PgAtomicPrivateAdmission` is now a real **local synthetic PostgreSQL transaction**, not a no-op callback. It enforces scope, qualified human membership, active purpose consent and shared ENG14 JTI before bounded engine dispatch; nevertheless the CI database login is password-authenticated, not physically clientcert-verified. A stolen correctly bound CI login can bypass TLS at the SQL boundary if permitted to call the broker, so this gate refuses managed-required tenants and must NOT be promoted to staging. The managed launcher has no approved external adapter; CI Docker uses a separate disposable replay fixture. Neither is a real external workload issuer nor Security/SRE signoff.

## 4. Required independent decisions on the FINAL commit

| Decision authority | Reviewer account / signature | Git SHA | Evidence digest | Decision | Current |
|---|---|---|---|---|---|
| Architecture owner ADR-003 and ADR-004/005 naming | NOT ASSIGNED | — | — | PENDING | NOT RATIFIED |
| Independent Security (identity, JWT, mTLS, PG, ENG14) | NOT ASSIGNED | — | — | PENDING | UNSIGNED |
| Independent SRE (network, PKI/secret ops, DR/RTO/RPO) | NOT ASSIGNED | — | — | PENDING | UNSIGNED |
| Independently credentialed professional specialist | NOT ASSIGNED | — | — | PENDING | UNSIGNED |
| Owner financial/provider authorization for future staging | NOT APPROVED | — | — | HOLD | NO DEPLOYMENT |

Qualified reviewers must inspect actual source, negative tests, risk exceptions and immutable artifacts; provider-specific runtime approval additionally requires externally attested resource IDs, real pg_stat_ssl/hostssl clientcert evidence, external issuer, network ACL denied probes, callback-to-DB proof, backup restore and cert rotation/revocation. A green CI result or signed fake fixture is not independent approval.

## 5. Acceptance sequencing and exact gate decision

1. Verify new security suite at final Git SHA with zero failed/skipped mandatory tests. Record workflow run link/artifact hashes on issue #81.
2. Architecture owner verifies canonical owner and adapter meanings, signs ADR-003 and ADR-004; independently approves the proposed ADR-005 number and canonical per-engine SPIFFE URI/trust domain issuer before any external enrollment.
3. Independent Security reviewer audits exact runtime and SQL privilege boundaries, replay/admission hook, identity chain, forged-GUC and consent races; gives attributable APPROVE/REQUEST_CHANGES/REJECT.
4. Independent SRE reviewer tests actual infrastructure after separately authorized spending, confirms network isolation, disaster recovery, alerting and rollback. Nothing is provisioned now.
5. Qualified professional independently verifies references, consent, contraindications, SOP and risk scope. No customer ENG-06 action or ENG-07 release without this gate.
6. Only then seek explicit A2 closure; a final product release requires a separate authorization. Do not merge or promote automatically.

**Current flags:** PREDEPLOYMENT_CODE_REVIEW=IN_PROGRESS until latest CI reconciled; STAGING_DEPLOYMENT=HOLD_PENDING_OWNER_COST; MANAGED_PKIX=NOT_ATTESTED; SECURITY/SRE/SPECIALIST=UNSIGNED; ADR_003_004_005=NOT_RATIFIED; A2=OPEN; ENG06_RELEASE=BLOCKED.
