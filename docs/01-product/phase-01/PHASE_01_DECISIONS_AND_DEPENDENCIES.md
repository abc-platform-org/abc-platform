# Phase 01 — Product Decisions, Open Questions and Upstream Dependencies

## Decisions explicitly supported by project user

| Decision ID | Description | Owner | Evidence | Status |
|---|---|---|---|---|
| P01-D01 | Product is salon-centric, specialist-operated, client-participatory on one physical shared display | saleheebrahimi2029-hub | Direct project directives and six reference UI screenshots | USER_DEFINED_PRODUCT_SCOPE |
| P01-D02 | AI Studio is the primary product differentiator and engineering critical path | saleheebrahimi2029-hub | Direct user request | USER_DEFINED_PRIORITY |
| P01-D03 | Advanced beauty service families remain full target scope despite staggered release | saleheebrahimi2029-hub | User-confirmed requirements | USER_DEFINED_SCOPE |
| P01-D04 | Selected Look proceeds to professionally reviewed Technical Execution Roadmap | saleheebrahimi2029-hub | Direct user request | USER_DEFINED_PRODUCT_SCOPE |
| P01-D05 | No at-home customer portal, no unsolicited external visual sharing | saleheebrahimi2029-hub | Explicit correction to initial requirements | USER_DEFINED_NON_GOAL |
| P01-D06 | Single accountable owner for all project build, governance routing and delivery tasks | saleheebrahimi2029-hub | Explicit current directive | USER_DIRECTIVE_ASSIGNED |

## Product recommendations requiring approval and trial

| Proposal | Scope | Current state | Evidence / next Gate |
|---|---|---|---|
| P01-P01 | Limited initial men's haircut / beard and haircut styling MVP verticals | PROPOSED, not a forced product decision | Validate qualified specialist, benchmark and commercial priority; G-01/G-03 |
| P01-P02 | Hair-color visual MVP only when separate color QA pass; chemical plan deferred | PROPOSED risk restriction | Qualified colorist SOP and VIS evidence; G-03/G-05 |
| P01-P03 | One product backend, logically independent 19 engine boundaries with isolated AI workers | PROPOSED architecture | ADR review + Phase-02 interface contracts |
| P01-P04 | V2 deep Salon OS and advanced services, V3 international SaaS | PROPOSED staged release positioning | Product owner accepts release matrix at G-01 |

## Gate-00 dependencies that are NOT waived by sole ownership

- G00-01: three missing parent historical sources (`DOC-001 v1.2`, `DOC-005 v1.1`, `CCR-001 v1.1`) must be recovered OR individually scoped exception with owner decision; [issue #2](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/2).
- G00-02: ten ADR review decisions remain proposed; [issue #3](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/3).
- G00-03: [issue #4](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/4) owner organizational appointment is now user-assigned, but independent specialist/security/privacy/QA review remains unresolved.
- G00-04: security/privacy [#5](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/5), qualified SOP/safety [#6](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/6), QA plan [#7](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/7), final Gate decision [#9](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/9).
- G01-01: historical KB derivative exact bytes referenced by KB-900 not yet independently verified; [issue #8](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/8), must be handled before knowledge pack migration.
- G01-02: no external specialist/safety attestation or consented benchmark dataset is presently verified. Service pack states remain NOT_RELEASED.

## Definition of scope freeze vs implementation freeze

- **Scope freeze:** Product owner explicitly accepts bounded release options, non-goals, accepted NFR categories and Phase-01 feature/acceptance matrix with specific SHA.
- **Engineering contract freeze:** Phase-02 schemas, APIs, service question profiles, visual processing contracts and exact authority transitions are reviewed and locked.
- **Implementation/release:** never implied by either documentation freeze.

## Owner-led progression safety

Single-owner team may author requirements and build code, but a separate *evidence function* is still mandatory: actual automated test run for code, reviewed trace for QA and qualified professional review where client safety, privacy or chemical application is involved. No assertion of independent audit based on the same author's own documents.

## Next unit of work

After user accepts staged product scope and Gate-00 gets an approved disposition, launch Phase-02 contracts using `FEATURE_RELEASE_MATRIX.csv` and `STORY_ACCEPTANCE_MATRIX.csv`, beginning with Session, Consent, Evidence, QuestionProfile, LookSpec, VisualJob, VisualQA and TechnicalPlan.
