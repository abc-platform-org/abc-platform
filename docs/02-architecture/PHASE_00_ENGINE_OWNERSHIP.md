# WP-000-01 — Engine Ownership and Boundaries

**All 19 engines have a proposed *role owner* but no named individual has been assigned.** This matrix does not claim deployed services, existing code, or model-specific validation.

| Engine | Responsibility | Source / migration | Proposed accountable role | Main output | Phases | Test / evidence obligation | Status |
|---|---|---|---|---|---|---|---|
| ENG-01 Durable Orchestration | workflow, events, checkpoints, retries | DOC-005/008; proposed durable runtime | Runtime Platform Lead | WorkflowState / NextAction | 02,04,11 | SES-01, OBS-01 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-02 Adaptive Consultation | intent, targeted questions, contradiction, stop | DOC-002/005/008 | Consultation / Conversation Lead | ConsultationProfile | 05 | PQ-01..03, SES-01 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-03 Evidence & Input Quality | assets, image quality, provenance | DOC-001/004 | Input and Evidence Lead | EvidencePackage | 04,07 | INP-01/02, SEC-02 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-04 Beauty Analysis | service-specific observations and attributes | DOC-004, KB-002 | Beauty Domain & CV Lead | AnalysisResult | 06 | ANA-01, safety review | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-05 Knowledge & Ontology | versioned sources, 39 legacy services and attributes mapping | DOC-003/004/011, KB-900 | Knowledge / Ontology Lead | GroundedKnowledge | 06 | KB-ID-MAP, RETR-01 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-06 Decision & Recommendation | hard filters, priority cascade, tradeoffs | DOC-007 v1.0; Library v1.1 | Decision Intelligence Lead | RecommendationSet | 06 | DEC-01, ABC-TC-019 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-07 Look Specification | requested style and parameter semantics | DOC-001/007, new Look schema | Look Model / Domain Lead | LookSpec | 06,08 | LOOK-01, TEC-01 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-08 Visual Segmentation | allowed regions/masks/hard boundaries | DOC-009 future mechanism | Computer Vision Segmentation Lead | RegionMaskSet | 07 | VIS-01/02 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-09 Controlled Generation | model invocation within requested constraints | DOC-009 future mechanism | Generative Image Systems Lead | CandidatePreview | 07 | VIS-03, provider benchmark | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-10 Image Compositing | merge with original, preserve excluded pixels | DOC-009 future mechanism | Image Processing Lead | CompositedPreview | 07 | VIS-02 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-11 Visual Quality Assurance | pixel diff, identity, fidelity, plausibility | DOC-010/015 | Computer Vision QA Lead | VisualQAReport | 07,12 | VIS-01..03, human review | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-12 Visual State & Version | immutable version DAG and selective revisions | DOC-008, new persistent state | Session / Visual State Lead | LookVersionRecord | 04,08 | VIS-04/05, SES-01 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-13 Service Feasibility | physically conditional execution checks | DOC-007 and Library FZ rules | Professional Feasibility Lead | FeasibilityResult | 09 | TEC-02, DOC-007 FZ | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-14 Safety & Policy | S0-S3 gates and non-bypassable limits | DOC-012, KB-011 | Safety/Policy Lead + Domain Reviewer | PolicyDecision | 04,09 | SAF-01..03, ABC-TC-001..020 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-15 Technical Planning | SOP-bound procedure graph and materials | User decision, KB-010/011, SOP gap | Professional Planning Lead + Specialist SME | TechnicalPlanDraft | 09 | TEC-01..03, SOP review | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-16 Specialist Validation | human review, signed audit and invalidation | User decision, Library DOC-007 | Identity & Human Validation Lead | ValidationRecord | 09 | TEC-04/05, SEC-03 | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-17 Output & Handoff | typed human/ops output with permissions | DOC-014 OUT-01..17 | Operations Integration Lead | HandoffRecord | 11 | INT-01, OUT contract audit | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-18 Business Intelligence | verified KPIs and explanations | User UI + new business scope | Data & Analytics Lead | BusinessInsight | 10,14 | BUS-01, KPI provenance | DESIGN_ONLY / PERSON_UNASSIGNED |
| ENG-19 Opportunity & Automation | propose/approve/execute actions | User UI + new business scope | Automation/Workflow Lead | ActionProposal / Job | 10,14 | BUS-02, SEC-03, approval tests | DESIGN_ONLY / PERSON_UNASSIGNED |

## Interface ownership rules

1. ENG-01 alone orchestrates durable workflow state; ENG-02 does not own database authority.
2. ENG-03 owns evidence provenance, not any diagnosis from images.
3. ENG-06 recommends but does **not** issue FZ-3 or `VALIDATED`.
4. ENG-07 owns structured Look intent; ENG-09 image output is not the source of truth.
5. ENG-08/10 own pixels/allowed masks; ENG-11 independently gates acceptance.
6. ENG-15 may generate a draft; ENG-16 alone records authorized specialist confirmation.
7. ENG-17 sends only authorized internal operations, not automatic client remote delivery.
8. ENG-19 may propose or run **approved** business actions, not invent bookings/payments.
9. ENG-14 safety policy cannot be bypassed by role, promotion or UI state.

## Unresolved architecture/deployment decision

Modular runtime and isolated workers are target **patterns** only. Actual implementation language, service boundaries, queues, AI model versions, budgets, concurrency, and named owners belong to Phase 02/04 and should not be asserted today.
