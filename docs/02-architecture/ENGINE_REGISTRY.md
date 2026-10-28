# Engine Registry — 19 Contract-Driven Engines

All `ENG-01..ENG-19` are **design responsibilities**, not claims of deployed microservices or trained independent models.

| ID | Engine | Scope | Required output |
|---|---|---|---|
| ENG-01 | Durable Orchestration | workflow, events, checkpoints, retries | WorkflowState / NextAction |
| ENG-02 | Adaptive Consultation | intent, targeted questions, contradiction, stop | ConsultationProfile |
| ENG-03 | Evidence & Input Quality | assets, image quality, provenance | EvidencePackage |
| ENG-04 | Beauty Analysis | service-specific observations and attributes | AnalysisResult |
| ENG-05 | Knowledge & Ontology | versioned sources, 39 legacy services and attributes mapping | GroundedKnowledge |
| ENG-06 | Decision & Recommendation | hard filters, priority cascade, tradeoffs | RecommendationSet |
| ENG-07 | Look Specification | requested style and parameter semantics | LookSpec |
| ENG-08 | Visual Segmentation | allowed regions/masks/hard boundaries | RegionMaskSet |
| ENG-09 | Controlled Generation | model invocation within requested constraints | CandidatePreview |
| ENG-10 | Image Compositing | merge with original, preserve excluded pixels | CompositedPreview |
| ENG-11 | Visual Quality Assurance | pixel diff, identity, fidelity, plausibility | VisualQAReport |
| ENG-12 | Visual State & Version | immutable version DAG and selective revisions | LookVersionRecord |
| ENG-13 | Service Feasibility | physically conditional execution checks | FeasibilityResult |
| ENG-14 | Safety & Policy | S0-S3 gates and non-bypassable limits | PolicyDecision |
| ENG-15 | Technical Planning | SOP-bound procedure graph and materials | TechnicalPlanDraft |
| ENG-16 | Specialist Validation | human review, signed audit and invalidation | ValidationRecord |
| ENG-17 | Output & Handoff | typed human/ops output with permissions | HandoffRecord |
| ENG-18 | Business Intelligence | verified KPIs and explanations | BusinessInsight |
| ENG-19 | Opportunity & Automation | propose/approve/execute actions | ActionProposal / Job |

## Engine clusters

A — Consultation / Evidence / Beauty / Knowledge / Decision / Look: ENG-02..07. B — Visual: ENG-08..12. C — Professional: ENG-13..16. D — Runtime/Handoff: ENG-01, ENG-17. E — Business: ENG-18..19. Safety ENG-14 additionally intercepts other clusters before dangerous release or actions.

## Ownership policy

For every engine before the phase gate: assign accountable engineering owner, input/output schema, invariant, failure matrix, test ID group, benchmark method, human reviewer when relevant, release state, instrumentation and resource budget. A tool/model provider is an adapter, not the owner of product state or professional validation.

## Independent maturity

`DESIGN_ONLY → CONTRACTED → IMPLEMENTED → TESTED → REVIEWED → RELEASED` with per-engine evidence. Runtime deployment boundaries may remain modular initially; tests, permission boundaries and contracts cannot be skipped.
