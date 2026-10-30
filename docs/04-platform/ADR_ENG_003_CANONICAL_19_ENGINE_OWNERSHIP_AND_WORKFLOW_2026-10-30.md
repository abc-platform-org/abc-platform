# ADR-ENG-003 — One canonical logical owner for all 19 ABC engines

**Engineering date:** 2026-10-30  
**Status:** PROPOSED TARGET / SOURCE-CONTROLLED CONTRACT REVIEW; NOT production approval or an independently signed architecture gate.  
**Supersession:** This is a *19-engine target-ownership reconciliation* of historical v1 and ADR-ENG-002 v2, **not a destructive replacement of either frozen protocol**.  
**Product scope:** in-person specialist + client on one shared salon display. Salon Business OS and downstream analytics remain linked but cannot authorize professional treatment.

## Decision and justification

There are two incompatible meanings for ENG04/05/06 today:
1. Historical `abc.internal.engine.synthetic.v1`: ENG04=analysis, ENG05=knowledge, ENG06=decision.
2. Frozen `abc.internal.engine.v2.draft`: ENG04=recommendation, ENG05=decision, ENG06=technical planning. It is genuine bounded Python code, but synthetic, untrusted professionally and not customer-ready.

The future 19-engine architecture retains **one canonical capability owner**, while keeping all current shipped/draft port identifiers unchanged. This avoids silently breaking consumers and prevents two engines from claiming the same domain truth.

### Canonical responsibility map

| Engine | Sole *logical* responsibility | Current code maturity |
|---|---|---|
| ENG-01 | Orchestration, state transitions and cross-service coordination | Bounded CI foundation |
| ENG-02 | Co-present consultation/session and purpose-based consent | Bounded CI foundation |
| ENG-03 | Durable evidence ingestion, input quality and lineage | Bounded CI foundation |
| ENG-04 | Beauty / visual observations and uncertainty; **not recommendation ownership** | Bounded CI analysis, separate pixel tools |
| ENG-05 | Expert knowledge and ontology provenance; **not decision ownership** | Bounded CI knowledge/signature tools |
| ENG-06 | Explainable decisions and non-executive style recommendations | Bounded CI decision, v2 role conflict |
| ENG-07 | Target Look specifications and controlled attributes | Independent engine absent |
| ENG-08 | Region segmentation and editable/protected masks | Independent engine absent |
| ENG-09 | Controlled image generation/transform/try-on | Independent engine absent |
| ENG-10 | Source/variant compositing, occlusion and rendering | Independent engine absent |
| ENG-11 | Independent visual fidelity QA (VQ01–VQ07) | Pixel-fidelity check currently embedded in ENG04 |
| ENG-12 | Immutable image/Look versions, selection CAS and recovery | Prototype-only interaction, no durable runtime |
| ENG-13 | Service-specific feasibility, risk and capability gate | Independent engine absent |
| ENG-14 | Standalone policy, consent, qualification and safety authority | Bounded CI security foundation |
| ENG-15 | Specialist-reviewable technical procedure plan, no auto-execution | Partial v2 code currently labeled ENG06 |
| ENG-16 | Qualified specialist authentication, review and signed approval | Partial signature primitive only |
| ENG-17 | Sanitized reviewed output and operational handoff | Independent engine absent |
| ENG-18 | Audited business KPIs and cross-service BI lineage | Independent engine absent |
| ENG-19 | Controlled automation and salon opportunity intelligence | Independent engine absent |

**Nineteen independent domain owners do not mean nineteen publicly accessible apps or immediately provisioned cloud services.** ENG01 and ENG14 are cross-cutting controls, and ENG18/19 are optional downstream, never dependencies for a safe completed consultation.

### Existing code migration: mandatory explicit adapters

| Existing boundary (preserved) | Present role | Canonical target | Safe migration prerequisite |
|---|---|---|---|
| ENG04 v2 recommendation | Draft Look recommendations | ENG06 decision plus ENG07 look specification | New explicit reviewed adapter, input/output schema migration and regression; no aliasing |
| ENG05 v2 decision | Candidate ranking/risk | ENG06 decision | Translate and validate signed knowledge refs; no ENG05 independent decision claim |
| ENG06 v2 technical-plan | Guarded generic plan template | ENG15 Technical Planning | Approved SOP + Look CAS + professional review; no auto treatment |
| ENG04 visual pixel QA | Region/face mask pixel invariants | ENG11 Visual QA | Independent trusted mask provenance and specialist VQ benchmarks |
| v2 professional source signature | Signed fixture source/SOP verification | ENG16 specialist validation | Independent issuer and professional qualification authority, revocation audit |

Statuses `UNMIGRATED` are deliberate. Do **not** change frozen v1, v2 schemas or the v2 engine IDs in place. A later promoted `abc.internal.capability.v3` (currently only `.v3.review`) requires separate producer/consumer adapters and explicit ADR review, data migration/rollback test, exact scoped JWT audience, negative provenance tests and signed qualification.

## Workflow contract and security

The proposed 17 ordered data-plane stages run:
`ENG02 → ENG03 → ENG04 → ENG05 → ENG06 → ENG07 → ENG08 → ENG09 → ENG10 → ENG11 → ENG12 → ENG13 → ENG15 → ENG16 → ENG17 → ENG18 → ENG19`.

ENG01 owns the transition/state machine. ENG14 owns denial, consent, risk and policy. Seven explicit blocking gates apply: consent before evidence processing; visual evidence and mask rights before segmentation; signed knowledge before decision; dual client+specialist selected Look CAS before feasibility; SOP/qualification before planning; independent qualified specialist signoff before handoff; separate consent and action policy before automation. See machine-readable graph for precise positions and exception routes.

Each handoff carries exact scoped tenant, branch, session, state version and correlation IDs, one canonical artifact type/digest, evidence refs and policy proof reference; every resulting artifact belongs to exactly one logical owner. Cross-service authenticated mTLS, signed JTI with one-time replay, durable ACK and independent authority checks are **not proven** merely by a valid JSON handoff.

A generic JSON Schema is available as `contracts/review/engine19_handoff.v0.schema.json`; it intentionally fixes `execution_authorized=false`, `customer_release_approved=false` and `status=CANDIDATE_FOR_EXTERNAL_AUTHORIZATION`. The test-only preflight checks schema, sequence and required policy-reference presence; it **never dispatches real services** or independently verifies a signature. A caller-supplied reference can never bypass ENG14.

The proposed shared-screen journey: specialist starts scoped session → client consent → validated media/evidence → safe observations → signed specialist knowledge → decisions/options → Look specs → authorized segmentation/generation/compositing/QA → versioned comparison and specialist/client Look selection → feasibility → evidence-gated technical plan → independent specialist validation → approved operational handoff. Business analytics/automation are decoupled events.

## Formal acceptance still open

- Registry: `governance/abc_engine_registry_19.v0.review.json` — 19 owners, 7 bounded CI foundations, 12 not independently implemented, zero G01–G10 COMPLETE.
- Workflow: `governance/abc_workflow_19.v0.review.json` — 17 data-plane stages, 16 **unwired** prospective handoffs, seven independently unprovisioned gates. Branches for human revision, safety cancellation and recovery are SPEC ONLY, not executable.
- CI: `scripts/validate_abc_19_engine_architecture.py` and negative tests prevent owner duplication, swapped stages, gate bypass, false status and v1/v2 semantic drift. Additional local runtime preflight checks prospective edges and never authorizes dispatch.
- Current `governance/engine_quality_registry.v1.json` remains the historical seven-engine quality baseline, not a final owner list. The accompanying `governance/abc_engine_quality_19.v0.review.json` explicitly materializes **190 OPEN G01–G10 slots** (19 logical owners × 10 independent gates) with zero independent attestations; `scripts/validate_abc_19_engine_architecture.py` rejects any fabricated PASS/COMPLETE, missing slot, forged signer or partial deletion. This matrix is a **blocker registry**, not a signed acceptance.
- Architecture owner signature, actual managed private deployment, real visual models/professional knowledge/SOPs, performance SLOs, real specialist approval, BI and automation remain open. No paid AI API is approved or needed for this spec-only work.
- W0 gate is **design implementation + CI verified**, *not* independently signed architecture release. W1 physical deployment and W2–W8 professional product completion remain open; no product release.
