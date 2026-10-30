# ABC W0 — 19-engine architecture ratification dossier

**Engineering date:** 2026-10-31
**Status:** DESIGN FREEZE CANDIDATE — NOT RATIFIED / NOT EXECUTABLE / NOT CUSTOMER-READY
**Scope:** specialist and customer together on one salon display; AI Studio, specialist plan and Salon Business OS.
**Baseline:** GitHub `saleheebrahimi2029-hub/abc-platform`, PR #56 head `3c4f978288d412ddb44f010a4162a35ad3a9ba1a`.
**Candidate artifacts:** `governance/abc_w0_engine_interfaces.v0.review.json`, `governance/abc_w0_ratification_manifest.v0.review.json`, `scripts/validate_abc_w0_ratification_candidate.py`.

## 1. Product vision and authoritative boundaries

ABC is an **in-person salon decision and execution-support platform**, not a remote customer-chat app or 19 GPT personalities. The specialist opens a scoped session; client consent and intake inform evidence-aware analysis; professional knowledge informs decisions; AI Studio produces bounded editable previews; the specialist and client jointly select a Look; feasibility and verified professional protocols generate a reviewable technical plan; an independently qualified specialist validates; an authorized operational handoff delivers a reviewed plan. The salon's Calendar/Clients/Services/Team/POS/Inventory/Marketing modules may subscribe to separately authorized events. BI/Automation must never bypass professional or privacy gates.

Each `ENG-xx` denotes **one canonical logical capability owner**, not an instantly deployed server. Implementations may be separated into engine-owned private workloads progressively, while contracts, data authority, security checks and independent acceptance remain isolated. W0 is a design-control phase, not a claim of trained, independent production engines.

## 2. Canonical domain ownership and machine evidence

`governance/abc_engine_registry_19.v0.review.json` stays the only canonical name/output ownership registry. The new interface matrix is a **derived consistency candidate**, not a competing authority. It materializes input artifact(s), output, dependencies, upstream/downstream edges, v3 review protocol, and deployment/acceptance status for each of the 19 engines. ENG-01 orchestration and ENG-14 governance operate as cross-cutting control-plane owners; the other 17 engines own the data-plane stages. Only a reviewed adapter may migrate earlier roles.

| Engine(s) | Responsibility |
|---|---|
| ENG-01 | Workflow/session authority and orchestration |
| ENG-02/03 | Purpose-bound consultation and verified evidence |
| ENG-04/05/06 | Beauty observations, professional knowledge, auditable recommendations |
| ENG-07/08/09 | Look specification, authorized segmentation and controlled generation |
| ENG-10/11/12 | Compositing, independent visual QA and durable look version/lock |
| ENG-13 | Service feasibility and uncertainty |
| ENG-14 | Consent, safety and policy authority |
| ENG-15/16/17 | Verified professional plan, independent specialist signoff, controlled handoff |
| ENG-18/19 | Tenant-scoped BI and approved opportunity/automation actions |

The canonical order is:
`02→03→04→05→06→07→08→09→10→11→12→13→15→16→17→18→19`.
It contains 17 stages and 16 prospective edges. ENG-17 ends the core customer journey; 18 and 19 are nonblocking optional business downstream.

### Preserved v1/v2 semantics and six proposed bridges

1. Legacy v1 ENG-04/05/06 = **Analysis/Knowledge/Decision**. Frozen v2 ENG-04/05/06 = **Recommendation/Decision/Technical Plan**. These are different contracts.
2. Frozen v2 ENG-04 recommendation → canonical ENG-06 decision and ENG-07 look input, only with two separately reviewed projections.
3. Frozen v2 ENG-05 decision → canonical ENG-06 evidence.
4. Frozen v2 ENG-06 plan → canonical ENG-15 planning candidate, not an approved SOP.
5. Legacy ENG-04 pixel checks → canonical ENG-11 QA evidence, not an independent visual QA pass.
6. Signature primitive attributed to v2 ENG-06 → ENG-16 review input, **not** a qualified specialist signoff.

The six projections remain `UNMIGRATED`; there is no automatic routing, engine renumbering, source forgery, in-place ABI mutation or silent V1/V2 upgrade.

## 3. Non-bypassable policy gates

| Gate | Before engine | Owner / hard condition |
|---|---|---|
| P0 Consent | ENG-03 | ENG-14; current, purpose-bound and non-revoked. **Additional prerequisite:** pre-capture consent in ENG-02 |
| P1 Visual | ENG-08 | ENG-14; authorized image handles, masks and source isolation |
| P2 Decision | ENG-06 | ENG-14; verified knowledge provenance and critical unknown policy |
| P3 Selected Look | ENG-13 | ENG-01; specialist + client confirmation, atomic CAS and current consent |
| P4 Technical SOP | ENG-15 | ENG-14; signed current professional SOP, feasibility, salon capability |
| P5 Handoff | ENG-17 | ENG-14; qualified specialist validation and non-revoked authorization |
| P6 Business | ENG-19 | ENG-14; separate purpose, approval and idempotent automation |

Every transition additionally requires scoped tenant/branch/session/version, immutable artifact kind+digest, source provenance, verified service identity, replay defense, expiry/revocation handling and durable receipts. Exceptional branches pause and persist, deny and cancel, or request explicit bounded revision; they never skip a gate. **Important gap:** the current canonical graph only encodes P0 before ENG-03. Pre-capture consent on ENG-02 is a mandatory ADR-ENG-004 requirement and must be represented in the next reviewed workflow revision before live media use; no claim that it already runs.

## 4. CI evidence versus release authority

[PR #56](https://github.com/saleheebrahimi2029-hub/abc-platform/pull/56) at the baseline head passed Foundation CI run 353 with **453 Python tests** and Documentation run 297. That includes bounded synthetic PostgreSQL16, worker Lease/ACK/DLQ, isolated physical CI login and local mTLS tests. It does not demonstrate an independently provisioned private managed identity, a trained beauty model, real client media processing, specialist sources, a deployed ENG-06 consumer or operational approval.

All 19 independent engine acceptance matrices remain G01–G10 `OPEN` (190 slots), engine completion count zero. The v3 review contract fixes `execution_authorized=false` and `customer_release_approved=false`. A blocked ENG-05→06 outbox is an audit record, **not delivery permission**.

## 5. W0 exit criteria and evidence required

- **Architecture owner:** explicitly accept ownership, control/data plane and semantic bridge strategy on the *exact final candidate commit*. Record independent review and signed ADR-ENG-003; no assumptions about old numbering.
- **Independent security reviewer:** sign ADR-ENG-004 only after threat-model review and negative evidence for tenant isolation, worker identity revocation, consent race, stale lease, replay, signature/proof forgery, pre-capture authorization, media retention and fail-closed controls.
- **Professional domain lead:** approve human confirmation boundaries, service-specific SOP provenance, qualification verification, STOP conditions, identity preservation and the difference between visual simulation and achievable salon work.
- **Platform/SRE:** approve network segmentation, managed issuer/PKI, DB grants, private staging migration, observability, logging, capacity/SLO acceptance criteria, backups and tested rollback.
- **Release governance:** source-locked reproducible CI plus future independent reviews; all deployment or customer release decisions recorded separately. G01 may be considered only when actual evidence and owners exist. Neither this PR nor its passing CI can set any G01–G10 to COMPLETE.

**Ratification disposition:** PENDING. No reviewers have been assigned or inferred from user permissions; no human signatures are created in this dossier.

## 6. Execution queue following W0 review

| Gate | Work package | Verifiable exit evidence |
|---|---|---|
| W1 | Private staging network, managed workload credentials, mTLS, PostgreSQL/RLS, key rotation, backup & recovery | Independent identity/security/operations evidence; no public worker |
| W2 | ENG-01/14 durable orchestration and policy transitions, ENG-02/03 contracts and replay, stable engine transport | Cross-tenant, revocation, concurrency, durability and fault-injection tests |
| W3 | ENG-04/05/06 analysis/knowledge/decision as independent capabilities; ENG-05→06 authorization-aware outbox consumer | Real private test identities, controlled ACK and contract/provenance negative tests |
| W4 | ENG-07→12 real visual path and AI Studio shared-screen workspace | Identity and edited-region fidelity benchmarks, visual QA VQ01..VQ07, human comparison |
| W5 | ENG-13, ENG-15, ENG-16 and ENG-17 professional workflow | Look lock, service feasibility, current SOP, signed specialist validation, stop conditions |
| W6 | Core Salon Business OS: clients/calendar/team/services/POS/inventory/reviews/notifications | Tenant-scoped transaction/audit, data quality and authorized handoff |
| W7 | ENG-18/19 BI and purpose-bound automations | KPI lineage, action idempotency, budget, privacy, cancellation tests |
| W8 | Full controlled pilot and separate product release | Security, professional, quality, performance, SRE and business acceptance |

W1 security/platform and Business OS data models must proceed in parallel with core execution; W6/W7 can never block a safe customer consultation. Never commit credentials, enable paid APIs or put an unqualified simulated plan in production to satisfy a milestone.

## 7. Exact next-action packet

1. Confirm the W0 candidate PR's exact-head CI.
2. Resolve architecture and threat-model review findings, including the missing explicit pre-capture consent checkpoint.
3. Obtain independent and attributable ADR-ENG-003/004 / professional / SRE reviews, each tied to an exact commit.
4. Only then issue a separate design freeze decision. Do **not** equate this decision with an engine completion or customer release.
5. Stage W1 privately and implement the bounded ENG-06 consumer with reject-first contracts, never automatically releasing the present ENG-05 outbox.

**Protected main, frozen v1/v2 and Notion contents are not changed by this dossier.**
