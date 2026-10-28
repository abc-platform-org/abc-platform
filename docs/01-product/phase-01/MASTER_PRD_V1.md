# ABC Master Product Requirements — Phase-01 / PRD v1.0

Status: `PROPOSED_SPEC_COMPLETE / APPROVAL_PENDING`. Organization owner: `saleheebrahimi2029-hub`. Historical baseline: `docs/01-product/PRD.md`; canonical target source precedence pending Gate-00 approval. PRD covers 18 ABC-F, 26 AIS and 20 PRD requirements, with no silent deletion or reinterpretation.

## 1. Problem and users

A customer cannot reliably communicate aesthetic intent in salon language; a stylist and customer can disagree about a photo, maintenance burden, feasible physical outcome and required tools/materials. Disconnected photo apps, consultation and salon appointments cause errors. ABC enables collaborative, auditable and controlled consult-to-service decisions; a visual preview is an approximation, not a physical outcome guarantee.

**Actors:** specialist controls session, client participates on SAME display; manager/reception/owner have separately authorized operational views; platform operator has least-privilege infrastructure administration. No client portal or remote consultation.

## 2. Required product outcomes

O-01 Dynamic, service-aware questions infer preference and explain top look candidates without generic repeated Q&A.  
O-02 Client/reference image provenance, consent, quality, angles and physical unknowns are tracked.  
O-03 LookSpec is versioned separately from image bytes and supports controlled Transform/Try On/Compare/Inspiration.  
O-04 Visual QA rejects identity/region drift; accepted changes survive subsequent edits, with immutable history.  
O-05 Specialist feasibility/safety assessment gates technical plan drafts, and signed review applies to exact LookVersion/SOP/evidence.  
O-06 Validated/conditional decisions hand off internally to scheduling, CRM, services and operations, never direct unapproved payment or stock mutation.  
O-07 Business OS derives metrics from actual events and enforces scoped Read/Recommend/Execute behavior.  
O-08 Architecture and rollout enforce tenant, branch, session and privacy boundaries from day one.

## 3. Product scope / release boundaries

| Stream | MVP | V2 | V3 |
|---|---|---|---|
| Consultation intelligence | One specialist-led flow; adaptive questions; service packs passing gate | Cross-service sessions, sophisticated preferences | Localized language variants and scale |
| Visual Studio | Selected haircut/beard verticals; permitted hair-color visual preview after separate QA; region lock, compare, version, QA | Multi-region, multi-view and advanced styles; more service packs | Cost/quality optimization and international coverage |
| Technical planning | Selected safe SOP-backed services; human review | Multi-stage advanced services, specialist packs | Workflow integrations across branches |
| Salon OS | minimal Clients/Calendar/Services/Team, basic Home and permission boundary | POS, inventory, business analytics, campaigns, Ask ABC actions | Internationalized SaaS/branch and enterprise operations |
| Security/governance | consent, RBAC, tenant and durable sessions | advanced audit/reporting | localization, residency, jurisdiction-specific controls |

**Release truth:** a field present in design screenshots does not constitute a real KPI or ready feature. All service packs must demonstrate availability, specialist qualification, SOP coverage and visual quality before release; no universal availability claim.

## 4. Core flow / behavioral requirements

**FR-001** Authenticated specialist creates a session with `tenant_id`, `branch_id`, `session_id`, optional client/appointment and purpose. Client sees only permitted shared information.  
**FR-002** Consent to image purpose/retention is captured before processing. A no-photo advisory route may remain if safe, with no invented preview.  
**FR-003** Domain-specific consultation identifies aesthetic goal, lifestyle, styling time, daily tools, change tolerance and service-specific risks. The question engine never repeats known questions without a stated conflict or confirmation reason.  
**FR-004** Evidence `KNOWN/OBSERVED/USER_REPORTED/INFERRED/UNKNOWN/REQUIRES_PROFESSIONAL_CHECK` remains provenance tagged; missing essential facts stop definitive claims.  
**FR-005** Candidate recommendation generation uses salon availability and hard constraints; explain reasons/tradeoffs without invented percentages. May return 1 or 2 choices if 3 qualified choices do not exist.  
**FR-006** LookSpec explicitly describes desired change, target regions, attributes, references, constraints, view needs and parent version; raw output images do not define the plan.  
**FR-007** Visual preview uses input/identity gates, segmentation, controlled generation, deterministic locked-region compositing, per-service QA and accepted-state version preservation.  
**FR-008** Four modes: Transform changes selected attributes, Try On transfers reference style not reference identity, Compare uses consistent base/framing and tradeoffs, Inspiration gives grounded diverse directions. `Technical Plan` is post-selection, not a fifth free-form image-editing mode.  
**FR-009** Client preferences, selected LookVersion and specialist validation are separate fields; the client cannot authorize physical service by selecting a preview.  
**FR-010** Technical plan draft requires validated ServicePack/SOP references, baseline evidence, qualified reviewer gate, materials, checkpoints, safety stop and aftercare. Unreliable chemical quantities/processing times are never guessed.  
**FR-011** A material change to image/LookSpec/evidence/SOP/plan automatically invalidates dependent signoff, with auditable rationale for any reviewed exception.  
**FR-012** Only authorized domain operations may update appointments, payments, inventory or marketing. Ask ABC must show Read, Recommend and Execute authorization context and operation outcomes.  
**FR-013** Session includes interruption, retry, cancellation, consent withdrawal, timeouts, stale-job exclusion, resumption and no-look-selected close.  
**FR-014** Each feature produces the evidence links in `FEATURE_RELEASE_MATRIX.csv` and `STORY_ACCEPTANCE_MATRIX.csv`.

## 5. AI Studio user-facing workspace

**Desktop/touch shared workspace**: top service family tabs (Hair, Color, Makeup, Skin, Nails, Beard, Grooming, Style); mode navigation (Transform/Try On/Compare/Inspiration plus gated Technical Plan); left panel Client, Service & Style, Advanced Controls and generate; center before/after canvas with zoom, fit, full-screen, mask overlay, status and version; right panel Look Gallery, styles, shortlist, Look Detail, selected comparison; bottom Inspiration/Palette/Details. Session state, image quality, provenance/uncertainty, undo/redo, QA, resume and private specialist review must be visible at relevant moments.

Service controls are semantically typed: haircut length/shape/volume/fringe/layers; hair color tone/depth/dimension/highlight placement; beard length/line/taper; makeup finish/intensity/occasion; nails shape/length/art; extensions length/volume; bridal composite. Sliders control *LookSpec*, not direct physical chemical parameters.

## 6. Performance / security / accessibility

**NFR-01** durable checkpointed server state with idempotent job handling; session recovery after browser closure.  
**NFR-02** tenant/branch isolation and backend RBAC; private notes never available to shared view.  
**NFR-03** scoped consent and derivative lifecycle, deletion/export policies reviewed per market.  
**NFR-04** visual metric thresholds are empirically calibrated on consented diverse dataset, not invented in specification.  
**NFR-05** touch/keyboard, readable Persian RTL and English LTR; accessible state, focus and error behavior.  
**NFR-06** model version, prompt, masks, output, evidence and evaluator linked by immutable trace.  
**NFR-07** asynchronous job status with progress, cancellation/retry, eventual completion or explicit failure, no unbounded spinner.  
**NFR-08** business KPIs derive from versioned event and transactional source truth.  
**NFR-09** encryption/backup, least-privilege infrastructure, secrets control and security testing are required; compliance badges only after verified.  
**NFR-10** service-specific change-type QA (hair color vs hair geometry vs beard, etc.) and multi-angle adequacy.

## 7. Formal acceptance

**Phase-01 document completion:** 18/18 ABC-F, 26/26 AIS and 20/20 PRD requirements have story, evidence objective, release assignment, owner and Gate; 11 service-pack families have release states; all roles and exceptions recorded, and CI runs. **Phase-01 Gate-PASS:** explicit owner acceptance plus resolution/accepted bounded exceptions for G-00 blockers and verified applicable domain/privacy reviews. Never report G-01 PASS solely from document CI.

## 8. Constraints and dependencies

Phase 00 currently `BLOCKED_FOR_FORMAL_APPROVAL`: 3 unrecovered Productization parents, unapproved ADRs and qualified reviewer evidence remain. Product owner assignment is now user-declared; independent technical/safety/privacy attestations are not. Exact API, schema semantics and performance budgets belong to Phase 02; full service model/visual proofs belong to Phases 04–12. See Phase-01 dependency ledger.

## 9. Traceability invariant

For every `ABC-F/ AIS / PRD`: `feature → user story → UI/engine/domain → data owner → API/schema (Phase-02 reserved) → tests → proof → release Gate`. The companion 64-row matrices expose it and mark implementation as not verified.
