# HISTORICAL SECURITY ANNEX — MISLABELLED ADR-ENG-004 (2026-10-31)

**Do not ratify this historical file as ADR-ENG-004.** The authoritative ADR-ENG-004 candidate covers v2-to-19 read-only adapters. The workload identity decision is now proposed as **ADR-ENG-005** in `docs/04-platform/ADR_ENG_005_MANAGED_WORKLOAD_IDENTITY_AND_TRUST_BOUNDARIES_2026-11-05.md`. This source snapshot is retained for audit traceability; its legacy heading below is historical and conveys NO approval. Renumbering is a technical design proposal, pending independent architecture/security ratification.

---

# ADR-ENG-004 — Private workload identity and cross-engine trust boundaries (W0 candidate)

**Date:** 2026-10-31
**Decision:** PROPOSED / NOT INDEPENDENTLY APPROVED
**Scope:** ABC in-salon shared-screen execution, 19 canonical capability owners.
**Precedes:** Any private runtime activation, automatic ENG-05 to ENG-06 delivery, v3 routing or customer processing.
**Related:** ADR-ENG-003; `abc_w0_ratification_manifest.v0.review.json`; PR #52 / #54 / #55 / #56.

## Context

CI demonstrates a bounded, synthetic and local-only PostgreSQL/loopback mTLS experiment; this is not a deployable private trust fabric. PostgreSQL permission group `abc_pipeline_worker` must remain **NOLOGIN**. An ephemeral CI `LOGIN NOINHERIT` using `SET LOCAL ROLE` tests narrow SQL authorization and physical `session_user` identity. This alone does **not** attest a managed workload identity in production.

The v3 review protocol must not reuse unapproved historical v1/v2 engine IDs as a semantic alias. Control-plane orchestration belongs to ENG-01. ENG-14 owns independent purpose-based policy and denial. Every data-plane engine owns its own bounded capability and provenance; this does not require 19 public servers.

## Proposed decision

1. **Private-by-default topology.** No public engine workers or unbounded database ingress. Run engines with network isolation, explicit service-to-service allowlists, minimal secrets, audited configurations and separately authorized staging migration credentials. Business OS web UI/API ingress is a separate trust boundary from engine transport.
2. **Managed identity per independent runtime.** Use externally verifiable identities (e.g. configured workload PKI / SPIFFE equivalent), short-lived credentials, audience-bound signed service assertions, revocation and rotation. Bind physical identity, tenant, consumer, target engine, service role and protocol version. `SET ROLE` alone is never authorization.
3. **Handoff authorization.** Check mTLS peer identity, independently verified JWT/JWKS or equivalent, token audience, certificate binding, one-time JTI, canonical edge/version, purpose-bound consent, current state/version, immutable payload SHA256 and ENG-14 decision. Reject missing/untrusted policy proofs. Re-evaluate revocation and state at both claim and ACK; stale work cannot commit or dispatch.
4. **Durable delivery.** Transactional inbox/consumer receipt, idempotency, claim with lease fencing, bounded retry, DLQ, incident reconciliation, outbox dispatch only after an independently approved consumer and release policy exist. A recorded `BLOCKED_PENDING_AUTHORITY` outbox row is *not* authorization.
5. **Consent at capture.** ENG-02 must check the appropriate consent *before* storing or processing any identifiable client image or sensitive intake (not just at ENG-03). P0 before ENG-03 remains necessary but insufficient as a stand-alone capture safeguard. No fallback to synthetic customer data.
6. **Human authority.** A selected Look lock requires both specialist/client confirmation and compare-and-swap (CAS) against current version. ENG-15 requires current service-specific verified SOP and feasibility. ENG-16 must verify a qualified, non-revoked independent professional before ENG-17 handoff. A model, self-signed fixture, reference ID, or sales module cannot substitute for authorization.
7. **Failure is fail-closed.** Deny on mismatched tenant, branch, session, state version, artifact lineage, identity, evidence, consent, policy, expired lease or missing specialist approval. Restore operations from a replayable audit trail, with operator-only quarantined recovery, not by skipping gates.

## Threats and mandatory negative evidence

| Threat | Mandatory evidence before operational acceptance |
|---|---|
| Shared worker / forged identity | Different physical workload IDs; revoked/rotated identity denied at claim and ACK |
| Cross-tenant / cross-branch replay | Scope and audience checks on ingress, persistence, dispatch and consumer |
| Stale session / revoked consent | Concurrent revocation and state-version races; no result or outbox on denial |
| Evidence or SHA mutation | Digest and provenance mismatch rejects without side effects |
| Duplicate/reordered/retried events | Exactly-once logical effect via durable receipt; bounded DLQ and replay |
| Compromised sender policy-proof string | Independent ENG-14 authorization lookup, never caller-controlled ALLOW |
| Image misuse / unconsented capture | ENG-02 pre-capture authorization; delete/retention and source isolation |
| Unqualified service SOP / model hallucination | Professionally approved sources and specialist credential verification |
| Look version race | Explicit dual confirmation + atomic CAS; stale Look denied |
| Automatic treatment or marketing | Explicit specialist gate, separate business purpose/consent and auditable action |

## Review and signoff protocol

Architecture owner reviews topology and semantics; an independent security reviewer examines policy bypass, authentication, encryption, consent and threat tests; a qualified professional reviewer examines service constraints and signatures; platform/SRE reviews secrets, deployment, disaster recovery, logs, rollback and SLOs. Every decision requires a real reviewer identity, immutable evidence reference, exact target commit and timestamp. CI-only success, assistant-generated text or repo write permission are not independent attestations.

**Open blockers:** no externally issued private workload trust, independently signed ADR-ENG-003/004, production-grade consent collection, specialist qualification authority or professional SOP library; no verified end-to-end ENG-05 to ENG-06 private execution. Production customer processing and deployment authorization remain **BLOCKED**.

**Impact:** no changes to frozen v1/v2, no migration to live v3, no merge to protected main under this candidate.
