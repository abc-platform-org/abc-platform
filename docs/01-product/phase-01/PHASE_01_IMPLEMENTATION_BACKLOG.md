# Phase 01 → Phase 02 / Engineering Backlog Handoff

**Organizational owner on every item:** `saleheebrahimi2029-hub`. **No code is implied delivered.**

| Work item | Inputs | Deliverable to Phase-02 | Depends on | Test evidence target |
|---|---|---|---|---|
| P02-001 | Session state and role matrices | Typed `ConsultationSession`, transitions and authorization contract | P01 user flows / GOV shared-screen | SES/SEC contract tests |
| P02-002 | Consent, image and reference requirements | `MediaAsset/ConsentRecord` schemas and policy API | P01 NFR + source reviews | SEC/PRIV contract tests |
| P02-003 | Adaptive questions | `QuestionProfile/Question/Answer/Evidence` schemas, selection policy | P01 consultation + service packs | PQ contract and semantic tests |
| P02-004 | Beauty analysis/decision | `AnalysisResult/RecommendationSet` and confidence/provenance taxonomy | Knowledge source lineage | ANA/DEC contract tests |
| P02-005 | Visual editing | `LookSpecification/LookVersion/EditOperation/Mask` schemas | P01 Studio acceptance | VIS contract tests |
| P02-006 | Image workers and QA | `GenerationJob/CompositingResult/QAReport` interfaces | P02-005 and visual safety policy | VIS negative/failure tests |
| P02-007 | Professional plan | `Feasibility/SOP/TechnicalPlan/Validation` contracts and hard stops | qualified SOP governance | TEC negative/approval tests |
| P02-008 | Operational integration | booking/Client/Team/Service/Handoff/quote messages | P01 Salon OS and tenant scope | INT/BUS contract tests |
| P02-009 | Security, tenancy | OIDC/RBAC policy engine, tenant projection, roles | P01 permission matrix + Privacy review | SEC negative tests |
| P02-010 | Release/feature gates | `ServicePack` lifecycle, audit and policy flags | P01 service matrix | QA/regression gate checks |
| P02-011 | UI design contracts | prototype component and error states, RTL/LTR | P01 journey/Studio workspace | UX/e2e design scripts |
| P02-012 | Evaluation harness plan | 120 Golden crosswalk + VIS/TEC/SES/BUS suite fixtures | P01 acceptance CSV + QA review | documented run plan |
| P02-013 | Build infrastructure | platform repo structure, tests/CI, env lifecycle | P02-001..010 contracts frozen | real CI and smoke tests |

### Story acceptance development rule

A GitHub issue/ticket for implementation must reference: one or more `ABC-F/AIS/PRD` IDs, accountable GitHub handle, exact Phase-01 story, data/API contract, errors, security policy, fixtures, test run and release Gate. Branch/PR code may not bypass unapproved SOP or reuse image-based aesthetics as proof of feasibility.

### Priority

**Critical path:** Consent → Session/Evidence → Adaptive Consultation → LookSpec/Decision → Visual Pipeline/QA/Version → Feasibility/Technical Plan/Specialist Validation → Operational Handoff.

**Parallel staged work:** Home/Clients/Calendar/Team/Service shell and basic data; advanced POS/Marketing/Automation wait until core decision/Studio passes visual proof and integration gates.
