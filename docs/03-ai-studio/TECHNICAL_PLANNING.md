# Technical Execution Planning — ENG-13..ENG-16

## Objective

After a client and specialist choose a specific, versioned look, build a **draft professional execution roadmap** grounded in real starting conditions, approved service SOP, salon capability, material/product requirements and professional findings. No automatic professional approval.

## Inputs

`selected_look_version`, `source_image_and_multi_view_evidence`, `client_reported_history`, `specialist_findings`, `service_pack_version`, `approved_sop_version`, `salon_materials_and_equipment`, `safety_flags`, `professional_review_role`.

## Output schema

```yaml
plan_id: uuid
plan_version: 1
session_id: uuid
selected_look_version_id: uuid
service_id: stable-service-id
sop_id: verified-sop-id-or-null
sop_version: version-or-null
baseline_evidence: []
blocking_unknowns: []
feasibility_status: PLAUSIBLE_OR_CONDITIONAL_OR_NOT_SUPPORTED_OR_UNKNOWN
stages:
  - stage_id: uuid
    name: protocol-grounded-stage
    preconditions: []
    instructions: []
    required_checks: []
    tools_and_materials: []
    parameter_sources: []
    stop_conditions: []
quality_checkpoints: []
time_and_complexity: conditional-estimate-or-null
aftercare: []
plan_state: DRAFT
specialist_validation: NOT_VALIDATED
```

## Procedure Graph

Compile SOP as a dependency-aware graph: pre-service condition → procedure stage → quality checkpoint → next stage / stop. A plan step may be added only when an approved SOP, compatible client facts and salon capabilities support it. `UNKNOWN` material facts block that step, not the entire consultation visualization necessarily.

## Service-specific requirements

- Haircut: anatomy/visual silhouette, validated length zones, partings, order, balance, blending, finishing, professional checks.
- Hair color: objective/current color, past chemical history, product-specific requirements, chemical risk and step gating. **No fabricated developer formula, mixing ratio, processing time or suitability clearance.**
- Makeup: planned style, regions, cosmetics, skin-related declared concerns, safe product handling, finish and checkpoints.
- Nails: current state, shape, materials, appropriate quality and safety checks.
- Keratin/smoothing: service/product SOP, contraindication and exposure policy, professional verification.
- Extensions: anchor/section, material choice, load and removal considerations, professional verification.
- Bridal composite: independent subplans and dependencies, separate review and holistic finishing.

## Validation lifecycle

`LOOK_SELECTED → PLAN_REQUESTED → EVIDENCE_CHECK → AWAITING_SPECIALIST_INPUT | DRAFT → SPECIALIST_REVIEW → REJECTED | REVISION_REQUIRED | CONDITIONALLY_VALIDATED | VALIDATED → HANDOFF`. Signed approval records exact look/SOP/evidence and reviewer. Material change invalidates sign-off.

## Operational handoff

Typed mapping to approved service, assigned qualified specialist, appointment duration estimate, stock availability check, work order and client record. AI cannot directly charge, book, change inventory or mark a service physically completed.

## Evaluation

`TEC-01..TEC-05`: look-to-procedure consistency; unknown critical data handling; no invented dangerous values; valid specialist authority and invalidation; salon capability truth. Expert reviewers are required for service/protocol release.
