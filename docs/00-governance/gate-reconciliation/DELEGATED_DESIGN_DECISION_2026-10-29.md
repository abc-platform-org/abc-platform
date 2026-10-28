# ABC-MEP-01.1 — Delegated Architecture, Product and Contract Decision
**Decision ID:** ABC-DDR-20261029-001  
**Decision date:** 2026-10-29  
**Decision authority:** Technical architecture decisions delegated to the assistant by the project's human owner in the active ABC conversation, following their direct direction to make the decisions on their behalf.  
**Recorded decision maker:** AI engineering consultant acting on **bounded design delegation**, not a real GitHub human reviewer, not a qualified salon specialist, and not legal/privacy certifier.  
**Approval scope:** `DESIGN_ONLY_CONDITIONAL` for G-00/G-01/G-02 architecture/product/interface baselines.  
**No production authorization:** All real-client, high-risk service, live image, external communications, payment, inventory, and launch operations remain under independent hard release gates.

## Decision 1 — Architectural authority and three missing parents

**Accept bounded design exceptions SRC-EXC-001 / SRC-EXC-002 / SRC-EXC-003** with status `DELEGATED_DESIGN_EXCEPTION_ACCEPTED`, preserving the original non-recovered source status and triggering an impact review if originals are found.

| Exception | Accepted design basis | Cannot be inferred | Review trigger |
|---|---|---|---|
| SRC-EXC-001: DOC-001 v1.2.0 | Current owner-defined salon-first product scope + verified historical DOC-001 v1.1.0 for compatible legacy terminology | Missing v1.2.0 clauses, continuity of GPT-only platform, prior approval | Recovered parent or material scope contradiction |
| SRC-EXC-002: DOC-005 v1.1.0 | New independently authored 19 **logical** engine boundaries + verified 10 logical legacy GPT roles from v1.0.2 | Missing v1.1.0 architecture or 19 deployed runtimes | Recovered parent, ownership/schema conflict, implementation benchmark |
| SRC-EXC-003: CCR-001 v1.1.0 | New explicit versioned design decisions, clause-by-clause independently verifiable source contracts | A historical change approval, source contents, parent immutability | Parent recovered, semantic migration contradiction |

**Strict migration rule:** old Notion documents stay immutable; newer changes are separate source-labelled ADR/PRD/contract artifacts. The legacy KB-900 16 derivative raw file bytes and hashes remain unverified, **therefore no migration or runtime activation of those derivatives is authorized**.

## Decision 2 — The ten ADRs (each separately accepted as a conditional DESIGN decision)

| ADR | Resolution | Mandatory evidence before its operational claim |
|---|---|---|
| ADR-001 | `ACCEPT_DESIGN_CONDITIONAL`: single modular application with independently testable logical ENG-01..19 boundaries and isolated CV/GPU workers, not 19 microservices | Performance, workflow and cost POC before physical service topology/tech stack freeze |
| ADR-002 | `ACCEPT_DESIGN_CONDITIONAL`: in-salon specialist-operated **shared display only**, customer participates without independent remote portal | Server-generated shared-safe field projection, negative privacy tests and step-up protected specialist mode |
| ADR-003 | `ACCEPT_DESIGN_CONDITIONAL`: immutable LookSpec/LookVersion independent of preview asset | Schema migration and version pinning integration tests |
| ADR-004 | `ACCEPT_DESIGN_CONDITIONAL`: evidence input QA → segmentation → controlled generation → deterministic composite → visual QA | Consented cross-service real-image benchmarks; identity/locked region thresholds |
| ADR-005 | `ACCEPT_DESIGN_CONDITIONAL`: hard visual QA pre-publication with **FAIL/INDETERMINATE fail-closed** | Measured QA, reference isolation, review calibration; preview QA is never physical feasibility |
| ADR-006 | `ACCEPT_DESIGN_CONDITIONAL`: append-only LookVersion DAG, CAS, immutable accepted state, stale worker rejection | Concurrency, out-of-order results and replay failpoint tests |
| ADR-007 | `ACCEPT_DESIGN_CONDITIONAL`: physical service feasibility distinct from visual plausibility and approval | Qualified specialist evidence for each service before actionable plan |
| ADR-008 | `ACCEPT_DESIGN_CONDITIONAL`: SOP-grounded **conditional draft** Technical Plan; server-verified qualified human approval only | Manufacturer-grounded SOP, material/chemical restrictions, professional validation and stop rules before real execution |
| ADR-009 | `ACCEPT_DESIGN_CONDITIONAL`: backend durable state machine, transactional outbox and idempotent business effects; **not** exactly-once delivery claim | Event producer authorization, replay/dedupe/cancel and crash-recovery runtime tests |
| ADR-010 | `ACCEPT_DESIGN_CONDITIONAL`: zero-trust tenant boundary, consent purpose, data retention controls and continuous negative tests from platform foundation | Independent security/privacy and jurisdiction-specific regulatory/legal assessment before real clients |

**Architectural coupling:** ENG logical interface separation is mandatory, deployment/process topology flexible; ENG-01 owns session state, ENG-12 Look revisions, ENG-16 specialist decision record, ENG-14 authoritative safety policy, ENG-17/19 only report successful business actions with real receipts. No model-generated "approval" bypasses these owners.

## Decision 3 — Phase-01 product and release scope

**Conditionally freeze P01 DESIGN baseline** at `7f940efdfeebd373825179abe3f94a11299e2749` with 18 ABC-F modules, 26 AIS operations, 20 PRD requirements, 64 traceable requirement IDs, four product domains, eleven salon service families and the UX/privacy role matrix.

- **MVP implementation candidates:** haircut/styling + men's haircut/beard + Core/Studio/conditional Technical Plan + minimum salon Clients/Calendar/Team/Services. Pilot service availability stays `NOT_RELEASED` until validated.
- **Hair color in MVP:** visual-only **research candidate**, disabled from real-client release until independent visual fidelity and specialist review. No chemical/bleaching/toning procedure authorized.
- **V2:** advanced service families and further Salon Business OS with individual release gates.
- **V3:** multi-branch global scale, localization, subscriptions; tenancy/security foundations must be implemented in MVP, **never delayed to V3**.
- **Explicit non-goals:** at-home customer portal, unconsented external customer media delivery, medical diagnosis, invented chemistry or live KPIs, unsupported financial/autonomous actions.

## Decision 4 — Phase-02 draft interface baseline

**Conditionally adopt P02 DESIGN contract candidate** at `164c512a944faf186144fdbb0d88dcabee871ade`:

- 19 standalone engine contracts, 34 JSON Schemas, 39 API paths/41 operations, 25 bound event types, five guarded State Machines; 17 historical output roles preserved.
- 64 requirement-to-contract traceability entries, 6 future detailed Salon OS domain functions `DEFERRED_RELEASE`.
- Twelve concrete contract design findings remediated in the draft; synthetic CI `40778026510` passed 33+39 core and 25+77 event cases = **174** synthetic fixture cases.
- This is **specification acceptance for implementation only**, not evidence that any of the 19 engines exists/runs, nor proof of runtime auth/policy correctness, verified CV fidelity or qualified SOP safety.

## Decision 5 — Explicit hard stop policy

**Adopt all nine risk-transfer records D-G00-001..009 as mandatory HARD RELEASE BLOCKERS**, not a waiver or professional signoff. Proof timing moves to respective G03..G09 service/data/technical gates; the existing `G-01_KNOWLEDGE_IMPORT_BEFORE_USE` restriction remains in force for frozen KB derivative bytes. No real-data processing, service actuation or business mutations are authorized by this document.

Fail closed at missing qualified SOP, invalid/withdrawn client consent, tenant data leak, absent independently measured Visual QA, missing required privacy/legal review, unexecuted 120 Golden scenarios, unreal receipts or unreleased ServicePack.

## Decision 6 — Gate semantics and merge authorization

- **G-00:** `DELEGATED_DESIGN_DECISION_RECORDED` once source/ADR exceptions and hard-stop overlays are committed and CI passes.
- **G-01:** `DELEGATED_PRODUCT_DESIGN_DECISION_RECORDED` once 64-feature source and staged scope are traceable, with successful document CI.
- **G-02:** `DELEGATED_CONTRACT_DESIGN_DECISION_RECORDED` once current typed contract tests and lineage validation pass.
- **This does NOT assert:** human GitHub PR review, qualified expert signoff, formal independent audit, original historical source recovery, or `RELEASED` product.
- **Merger instruction interpretation:** the owner had already directed doing whatever is necessary to close design phases and now explicitly delegated decision-making; subject to GitHub branch policy and successful exact-head CI, authorize staged merging of **documentation/design PRs only**: governance #15 → branch of #1, #1 → main, #10 → main, #12 → main. Preserve all original source files, verify each SHA/diff/CI, never force-push. Stop if GitHub requires an independent review that has not been submitted.

**Record integrity:** do not impersonate the owner in GitHub review. State in audit that this is a *delegated technical decision authored by the assistant* based on explicit chat instruction. The issue review record may note the owner's delegation, but not falsely say they personally inspected all contracts.

## Remaining open work despite design decisions

Qualified salon SOP/chemical review; professional service readiness; privacy and data governance; real Visual QA benchmarking; live event/run security; actual 19-engine implementations; end-to-end data/transaction correctness; 120 executable Golden scenarios; 16 frozen KB derivative byte reconciliation. These are separate hard gates, and must never be closed by Design-Only decisions.
