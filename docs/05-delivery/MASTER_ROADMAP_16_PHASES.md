# ABC-MEP-01.1 — 16-Phase Master Engineering Program

**Official proposed execution order**. Engineering does not advance via visual completion or unchecked checklist. Each phase requires documented outputs, actual test evidence and signed gate decision. Some business work and UI work can overlap after foundational contracts, but shared dependency interfaces are fixed first. No invented durations; estimate from actual team capacity and baseline benchmarks.

## Release streams

- **P0:** evidence of visual feasibility and architecture/contract clarity.
- **MVP:** specialist-operated shared-screen pilot for service packs which pass their own gates, not all beauty categories.
- **V2:** expanded advanced services, multi-region preview, business functionality.
- **V3:** multi-tenant international product.

## Phase table

| Phase | Title | Outputs | Acceptance gate |
|---|---|---|---|
| 00 | Recovery & Canonical Rebaseline | SOURCE_REGISTER, AUTHORITY_MATRIX, MIGRATION_MATRIX, DEFECT_REGISTER, baseline report | All known scope has owner/version/source; conflicts marked unresolved, none silently overridden. |
| 01 | Product Definition & PRD Freeze | PRD, FEATURE_INVENTORY, service coverage, role matrices, story acceptance criteria | Every feature has explicit acceptance and MVP/V2/V3 placement. |
| 02 | Architecture & Interface Contract Freeze | Architecture decision records, OpenAPI/schema draft, data model, interfaces, contract tests | No high-priority engine-to-engine interaction lacks typed contract or owner. |
| 03 | UI/UX Design System | Design tokens, component specification, interactive prototype, UX test scripts | All critical workflows demonstrate accessible, correct role boundaries in prototype. |
| 04 | Platform Foundation | Deployable skeleton, authenticated session API, image policy, base observability | Persist/resume session; deny unauthorized access; job replay/idempotency tests pass. |
| 05 | Adaptive Consultation Engine | ENG-02 v1, question registry, conversation UI, consultation test suite | No duplicate or irrelevant questions in golden scenarios; missing critical safety data not bypassed. |
| 06 | Beauty Knowledge, Analysis & Decision | ENG-03..07 valid contracts, approved knowledge packs, reproducible recommendation outputs | Unsupported candidates not ranked as available; no invented probability or third option. |
| 07 | Visual Studio Core / Proof | ENG-08..11, initial preview UI and QA suite | Mask leakage and QA fail gates verifiable; no unvalidated preview displayed as approved. |
| 08 | Professional Visual Iteration | ENG-12, AIS interactive workspace, regression set | Changing one approved attribute does not silently destroy unrelated accepted edits. |
| 09 | Technical Execution & Specialist Validation | ENG-13..16, specialist plan workspace, validated plan records | No executable plan without required evidence, approved protocol and human authorization. |
| 10 | Salon Business OS | 18 module ownership implementations and transactional API contracts | Live metrics trace to data; financial/stock changes require approved domain action. |
| 11 | End-to-End Integration | E2E scenario fixtures, trace graph, observed pilot walkthrough | IDs, versions, decisions and role permissions consistent throughout workflow. |
| 12 | QA, Security & Expert Pilot | Test evidence, signed severity decisions, calibrated release thresholds | No SEV-0/1 blocking findings; all mandatory gates PASS with referenced evidence. |
| 13 | Controlled MVP Release | Pilot release record, runbooks, rollout metrics, incident plan | Only individually released service packs exposed; deployment and rollback demonstrably safe. |
| 14 | V2 Advanced Services | Advanced service packs, expert-reviewed SOPs, E2E and regression evidence | Each released pack independently passes technical and specialist gates. |
| 15 | V3 International SaaS | International release candidates and compliance assessments | Tenant isolation and locality/privacy/ops gates evidenced per market. |

## Detailed phase runbooks

### Phase 00 — Recovery & Canonical Rebaseline

**Work:** Recover Notion/Library/GitHub source inventory; map current product decisions and conflicting baselines; register gaps.

**Artifacts:** SOURCE_REGISTER, AUTHORITY_MATRIX, MIGRATION_MATRIX, DEFECT_REGISTER, baseline report

**Exit Gate:** All known scope has owner/version/source; conflicts marked unresolved, none silently overridden.

**Dependencies / concerns:** No modifying legacy originals; main branch untouched.

### Phase 01 — Product Definition & PRD Freeze

**Work:** Confirm shared-screen roles, 18 cross-product features, 26 AIS features, 20 PRD items, 17 legacy outputs; define service boundaries and real use journeys.

**Artifacts:** PRD, FEATURE_INVENTORY, service coverage, role matrices, story acceptance criteria

**Exit Gate:** Every feature has explicit acceptance and MVP/V2/V3 placement.

**Dependencies / concerns:** Domain assumptions and no-at-home workflow are frozen.

### Phase 02 — Architecture & Interface Contract Freeze

**Work:** C4 boundaries, 19 engine contracts, event and state schemas, Question Profiles, service pack and SOP contracts, business action authorization, ADRs and threat model.

**Artifacts:** Architecture decision records, OpenAPI/schema draft, data model, interfaces, contract tests

**Exit Gate:** No high-priority engine-to-engine interaction lacks typed contract or owner.

**Dependencies / concerns:** Phase 00 and 01 accepted.

### Phase 03 — UI/UX Design System

**Work:** Translate six images into responsive professional screen components; desktop/touch, RTL/LTR, shared vs privileged display, errors, visual history, Technical Plan.

**Artifacts:** Design tokens, component specification, interactive prototype, UX test scripts

**Exit Gate:** All critical workflows demonstrate accessible, correct role boundaries in prototype.

**Dependencies / concerns:** Design reference images are concepts, not implementation proof.

### Phase 04 — Platform Foundation

**Work:** Set up repo, branch protections, CI, dev/staging/prod plans, backend/domain modules, RBAC, consent, durable workflows, database, object store, visual jobs, evaluation harness.

**Artifacts:** Deployable skeleton, authenticated session API, image policy, base observability

**Exit Gate:** Persist/resume session; deny unauthorized access; job replay/idempotency tests pass.

**Dependencies / concerns:** Use measured infra targets, not invented SLAs.

### Phase 05 — Adaptive Consultation Engine

**Work:** Build service question profiles, response normalization, contradiction handling, value-ranked question selector, stop rules and specialist override.

**Artifacts:** ENG-02 v1, question registry, conversation UI, consultation test suite

**Exit Gate:** No duplicate or irrelevant questions in golden scenarios; missing critical safety data not bypassed.

**Dependencies / concerns:** Need expert-approved consultation variables per released service.

### Phase 06 — Beauty Knowledge, Analysis & Decision

**Work:** Migrate legacy knowledge/service IDs, per-service evidence analysis, hard filters, qualitative cascade, recommendation explanation, LookSpec.

**Artifacts:** ENG-03..07 valid contracts, approved knowledge packs, reproducible recommendation outputs

**Exit Gate:** Unsupported candidates not ranked as available; no invented probability or third option.

**Dependencies / concerns:** Legacy 39/45 IDs validated for migration, not blindly assumed current.

### Phase 07 — Visual Studio Core / Proof

**Work:** Implement input QA, mask generation, preview adapter, deterministic compositing and visual QA for selected verticals; instrument real metrics.

**Artifacts:** ENG-08..11, initial preview UI and QA suite

**Exit Gate:** Mask leakage and QA fail gates verifiable; no unvalidated preview displayed as approved.

**Dependencies / concerns:** Real multi-angle/skin tone/texture dataset, professional labeling and consent required.

### Phase 08 — Professional Visual Iteration

**Work:** Implement version DAG, locked regions, semantic slider revisions, compare, inspiration, palette, Undo/Redo, stale output detection, selective regrowth.

**Artifacts:** ENG-12, AIS interactive workspace, regression set

**Exit Gate:** Changing one approved attribute does not silently destroy unrelated accepted edits.

**Dependencies / concerns:** Depends on visual core and versioning contract.

### Phase 09 — Technical Execution & Specialist Validation

**Work:** Implement SOP registry, procedure DAG, evidence and safety gates, materials resolver, conditional plans, specialist approval and invalidation.

**Artifacts:** ENG-13..16, specialist plan workspace, validated plan records

**Exit Gate:** No executable plan without required evidence, approved protocol and human authorization.

**Dependencies / concerns:** Each service separately professionally reviewed.

### Phase 10 — Salon Business OS

**Work:** Build core CRM, services, staff, calendar and later POS, inventory, analytics, reviews, marketing, automations and Ask ABC with source-linked data.

**Artifacts:** 18 module ownership implementations and transactional API contracts

**Exit Gate:** Live metrics trace to data; financial/stock changes require approved domain action.

**Dependencies / concerns:** Workstreams can run parallel; pilot relies on minimal core.

### Phase 11 — End-to-End Integration

**Work:** Connect physical salon session from consent through questions, analysis, visual revisions, selected look, plan, approval and operational handoff.

**Artifacts:** E2E scenario fixtures, trace graph, observed pilot walkthrough

**Exit Gate:** IDs, versions, decisions and role permissions consistent throughout workflow.

**Dependencies / concerns:** No regression to legacy GPT-only session context.

### Phase 12 — QA, Security & Expert Pilot

**Work:** Execute 120 inherited cases and new VIS/TEC/SES/BUS/SEC cases; perform threat tests, specialist panel review, usability and latency/cost benchmarks.

**Artifacts:** Test evidence, signed severity decisions, calibrated release thresholds

**Exit Gate:** No SEV-0/1 blocking findings; all mandatory gates PASS with referenced evidence.

**Dependencies / concerns:** Written test cases alone never count as executed.

### Phase 13 — Controlled MVP Release

**Work:** Staging/prod cutover, training, support, rollback, capability flags, restricted pilot, monitoring, human feedback and release review.

**Artifacts:** Pilot release record, runbooks, rollout metrics, incident plan

**Exit Gate:** Only individually released service packs exposed; deployment and rollback demonstrably safe.

**Dependencies / concerns:** No false claim of production capability.

### Phase 14 — V2 Advanced Services

**Work:** Develop nails, makeup, bridal composite, corrective color, keratin, extensions, multi-region multi-view QA and business system depth.

**Artifacts:** Advanced service packs, expert-reviewed SOPs, E2E and regression evidence

**Exit Gate:** Each released pack independently passes technical and specialist gates.

**Dependencies / concerns:** Do not expose a service before full criteria.

### Phase 15 — V3 International SaaS

**Work:** Multi-tenant enterprise ops, multi-branch, localization, billing, performance, security/privacy regional policies, DR and international support.

**Artifacts:** International release candidates and compliance assessments

**Exit Gate:** Tenant isolation and locality/privacy/ops gates evidenced per market.

**Dependencies / concerns:** A translated screen is not sufficient for an international launch.

## Dependency graph

```text
00 → 01 → 02 → {03 UX, 04 Foundation}
04 → 05 Questioning → 06 Evidence & Decision
03 + 04 + 06 → 07 Visual Core → 08 Visual Iteration
06 + 08 + validated SOP → 09 Technical Planning
04 → 10 Business OS (parallel controlled workstream)
09 + 10 core → 11 Full Integration → 12 QA & Pilot → 13 MVP
13 → 14 V2 → 15 V3
```

## Phase completion definition

Contracts reviewed; implementation merged through PR after CI; tests executed and cited; vulnerabilities addressed; specialist approval where needed; release notes, rollback and observability available; gate reviewer/decision documented. `NOT_STARTED`, `IN_PROGRESS`, `IMPLEMENTED`, `TESTED`, `PASSED`, `BLOCKED` are real states backed by proof, not personal optimism.
