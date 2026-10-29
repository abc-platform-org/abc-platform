# ABC — Seven Engine Definition of Complete (EDOC-01)

**Status:** quality policy recorded; 7 engine acceptance records OPEN; **0 COMPLETE**.  
**Source of truth:** `governance/engine_quality_policy.v1.json` and `governance/engine_quality_registry.v1.json`.  
**Date:** 2026-10-30. Product scope: specialist and client jointly at one salon display.

## Ten non-compensatory gates

| Gate | Owner / verification | Acceptance proof |
| --- | --- | --- |
| G01 Architecture | Product architect | Approved target engine ownership, ADR and traceability to ABC vision |
| G02 Capability | Product and domain QA | Required behaviours, exceptions and real feature tests; no synthetic stand-in |
| G03 Contracts | Architecture + integration | Typed/versioned ports, input/output validation, compatibility and provenance |
| G04 Independence | SRE | Separate actual deploy, service account, identity, restart, fault isolation |
| G05 Security / privacy | Independent security | mTLS, RLS, consent, tenant isolation and negative threat tests |
| G06 Reliability | SRE / QA | Durable ACK, idempotence, DLQ, retries, rollback and disaster recovery |
| G07 Performance | Performance QA | Approved measurable SLO and reproducible p50/p95/p99, saturation, load |
| G08 Specialist quality | Qualified domain reviewer | Approved SOP and specialist quality/safety/feasibility evaluation |
| G09 Operations | SRE | Trace/metrics/alerts, versioned runbooks, restore and incident drills |
| G10 Independent signoff | Separate professional and security reviewers | Trusted independent evidence signatures tied to exact SHA, manifest and scope |

**All ten gates are mandatory.** A strong score on one gate cannot compensate for an incomplete gate. Unit-test success is engineering evidence only, not professional acceptance. Real-world evidence, independent accountable signatures and final release governance are distinct. No score averaging or artificial overall percentage.

## Status and evidence control

- `IN_PROGRESS`: some code or synthetic tests exist; at least one required gate is open.
- `BLOCKED`: an active critical blocker prevents advancing or retesting a gate.
- `COMPLETE`: only after every gate is evidenced and independently verified, all critical blockers closed and a signed completion record binds engine ID, exact deployed artifact/commit SHA, evidence manifest digest, environmental scope, verified reviewer identities and dates.
- `PRODUCTION_RELEASE_APPROVED`: **separate decision** requiring product-wide E2E, privacy/security, financial and rollback approvals. An engine being COMPLETE never automatically opens product release.

External trusted verifier, reviewer credentials and actual cloud/PKI are not currently configured. The automated baseline validation deliberately refuses a `COMPLETE` assertion. Future acceptance code must consume externally verified signatures, not a boolean or self-filled JSON record. The existing signoff evidence verifier in PR #41 remains NOT a release authority.

## Engine-specific domain exit criteria

| ID | Objective capability for target | Critical current gap |
| --- | --- | --- |
| ENG-01 | Orchestrate verified in-person sessions across all approved states/operations, timeouts, retries and policy transitions | 41 v1 operations: 2 local harness, 39 unimplemented; only narrow safe state transition allowed |
| ENG-02 | Validated consultation, client record, service intake, active consent, session timeline and provenance | Synthetic intake and missing real multi-service consent lifecycle |
| ENG-03 | Independent reliable evidence ingestion with Claim/Lease/ACK, fencing, lineage and poison-queue recovery | Production DB identity, load and multi-worker resilience not demonstrated |
| ENG-04 | Identity-preserving visual understanding and grounded recommendations with reference & uncertainty fidelity | Synthetic non-media analysis only; proposed target role mismatch |
| ENG-05 | Evidence-grounded specialist decision, contraindication filters, uncertainty and explainability | Offline knowledge fixture only; proposed target role mismatch |
| ENG-06 | Selected-look-to-technical-plan engine, feasibility, equipment/material parameters, stop checkpoints, specialist validation | Currently synthetic decision filter, **not** Technical Planning |
| ENG-14 | Specialized service policy enforcement, permission checks, consent, professional SOP, audit and independent reviews | Draft S1–S3 policies; qualified external signatures absent |

## Quantitative SLO policy

Do not invent performance numbers as a claim of meeting a target. Before G07 evaluation, approve an engine-specific benchmark manifest containing: p50/p95/p99 latency budgets, error budget, expected concurrency, throughput, cold-start, resource envelope, hardware tier, input/fixture mix, duration, failure-injection scenario, reproducibility and test owner. Then measure against those **approved values**. A synthetic benchmark with known answers never replaces a representative real-world domain evaluation.

## Baseline facts and non-release boundary

PR #42 at `c223e8a194870ce8091e571952c20ba8a96e5f0b`: 299/299 foundation tests; real CI TLS1.3 API/engine and disposable PostgreSQL clientcert tests. These verify **laboratory integration**, not live private deployment, production identity, computer vision quality or an approved professional procedure. The baseline engine quality registry therefore records **70 open gate slots** and **zero COMPLETE**.

The architectural responsibility drift is documented in `ADR_ENG_001_ENGINE_RESPONSIBILITY_REALIGNMENT_2026-10-30.md`, pending formal owner acceptance. Do not modify frozen `contracts/v1` through this gate workstream.
