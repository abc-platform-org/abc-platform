# ABC A2 — SPIFFE trust-boundary isolation (ADR-ENG-005 review candidate)

**Date:** 2026-11-10
**Decision state:** Engineering correction in a separate DRAFT review branch; **NOT** independently ratified
**Parent proposal:** PR #88 (120-second JWT contract correction); original evidence PR #78 head `026e1fb174919278e3c2d73442be10b4f11675a4` remains immutable
**Tracking:** #87, #58 (Architecture), #84 (Security), #81 (A2), #63 (cost hold)

## 1. Two different admission surfaces

| Surface | Required workload principal | Admission rules | Forbidden crossover |
|---|---|---|---|
| Private HTTP staging API `private_api_mtls.py` | Explicitly pinned `spiffe://abc.internal/gateway/<gateway-id>` | TLS 1.3 mutual certificate chain plus exact URI-SAN allowlist; downstream human OIDC and PostgreSQL RLS separate | All `/engXX/<worker>` and `/staging/eng-XX` engine SANs |
| Engine-to-engine mTLS `service_mesh_identity.py` | Exact `spiffe://abc.internal/staging/eng-XX` certificate SAN and signed JWT `sub` | RS256 pinned issuer/JWKS, `aud=abc-engine:ENG-YY`, distinct consumer binding, `cnf` certificate SHA256, UUID4 JTI, <=120s, durable atomic ENG-14/PG gate | Gateway SANs, historical per-consumer/per-engine engine identities, wrong audience/consumer, forged policy ALLOW |

This correction **does not establish two independent managed CAs or a live mesh**. Both surfaces use a candidate `abc.internal` trust domain; external issuer ownership, distinct key issuance, revocation, network separation and provider-independent attestations remain OPEN.

## 2. Exact security change (candidate for independent review)

1. Tighten the private HTTP API mTLS caller allowlist to **gateway namespace only**, while preserving support for multiple exact approved gateway IDs (maximum 16). Reject unknown, mixed, duplicated, wildcard, whitespace and engine SAN entries.
2. Validate the allowlist **again** at the certificate-check boundary and server constructor; caller-supplied or manually assembled `frozenset` objects must never authorize obsolete engine SANs.
3. Preserve the exact canonical engine verifier with issuer/audience/subject/certificate bindings and PostgreSQL atomic authorization. No relaxation, auto-alias or implicit compatibility bridge. Old v1/v2 engine protocols remain frozen.
4. Preserve the staging cost hold and ENG-06 review-only release guard. A valid private API mTLS gateway certificate is **not** a human professional identity, ENG-14 consent approval or right to execute a salon treatment.

This decision is fail-closed for previously permitted legacy private-API engine callers. An operator who currently relies on `spiffe://abc.internal/eng03/eng03-worker` **must not migrate via permissive alias**. Any legitimate engine-to-API communication requires a separate reviewed gateway-proxy architecture with independently authenticated source identity, explicit role delegation, scope proof and replay-safe policy checks.

## 3. Negative and positive test cases proposed in source

| Evidence file | Acceptance cases | Current execution |
|---|---|---|
| `test_private_api_mtls.py` | two approved gateway IDs allowed; reject legacy and canonical engine SANs, wildcard, malformed/cross-domain/mixed allowlists; direct forged allowlist denied before server bind; unauthorized socket closed | CODE COMMITTED, **NOT RUN** on current GitHub head |
| `test_private_api_network_mtls.py` | disposable TLS1.3 real gateway certificate allowed; no certificate, unapproved gateway, CA-signed legacy engine and CA-signed canonical engine rejected | CODE COMMITTED, **NOT RUN** |
| `test_private_engine_mtls.py` | CA-signed **gateway certificate** cannot cross into independent engine even with cryptographically bound signed JWT; wrong single JWT audience rejected; existing signed identity/consumer/multi-audience/replay/JTI controls retained | CODE COMMITTED, **NOT RUN** |
| `test_eng14_transition_gate.py` | Gateway URI, legacy engine URI, canonical engine URI and ENG-03 engine name cannot substitute for the qualified human actor on S0 checkpoint | CODE COMMITTED, **NOT RUN** |
| `test_a2_adr005_candidate_contract_consistency.py` (parent PR #88) | candidate JWT TTL 120 seconds, seven unissued principals and all unapproved routes/proofs fail closed | CODE COMMITTED, **NOT RUN** |

Static source comparison and bounded previously successful synthetic CI tests **are not** execution evidence for these newly added cases. PostgreSQL16 integration, real operator-managed issuer, cert rotation/revocation, independent Security and SRE signoff remain unresolved.

## 4. Review and release dependencies

- Architecture owner: review ADR-003/004 and proposed ADR-005, the direct gateway-only restriction and any future explicit adapter/delegation design; attributable decision on exact reviewed SHA.
- Independent Security: threat model for compromised gateway, untrusted engine SAN, mixed allowlist, wrong audience, spoofed ENG-14 approval, cross-tenant/revoked consent; validate full source and tests on a real local checkout; review issuer/CA separation after cost authorization.
- Independent SRE: confirm private topology, issuer custody, network default-deny, deployment/rollback and rotation under a separately approved operator plan.
- Qualified professional: source rights, SOP and specialist signoff remain separate from this transport change.
- Developer: **do not merge** this stacked draft PR or parent PR #88 into PR #78 until exact-head Python test runs, regression, immutable source baseline/evidence-index revalidation and independent review are completed. A2 packet validator presently permits only five governance paths from its prior tested code SHA; this PR changes runtime/test sources.
- Owner: **no additional spend** and no unapproved GitHub-hosted Runner execution until an eligible free allowance exists. GitHub Actions billing gate remains blocked.

**Fail-closed outcomes:** `ADR-ENG-005=REVIEW_PENDING`, `SECURITY_SIGNOFF=NOT_RECEIVED`, `A2=OPEN`, `STAGING_DEPLOYMENT=ON_HOLD_COST_APPROVAL`, `ENG06_RELEASE=BLOCKED`, `ENG07_DISPATCH=BLOCKED`.
