# WP-000-03 — Qualified Specialist, Safety and SOP Authority Policy

**State:** `POLICY_DRAFT / QUALIFIED_REVIEW_PENDING`; [issue #6](https://github.com/saleheebrahimi2029-hub/abc-platform/issues/6).

## Non-negotiable clinical/professional boundary

`VISUAL_QA_PASS` is **not** `SERVICE_FEASIBLE`; `LOOK_SELECTED` is **not** `PROFESSIONALLY_VALIDATED`; `PLAN_DRAFT` is **not** `SERVICE_AUTHORIZED`.

ENG-15 may **draft** only when required evidence is sufficient for that level. ENG-16 records authenticated specialist confirmation constrained to a specific look, verified findings, SOP and plan version. ENG-14 imposes S0–S3 backend safety limits and cannot be bypassed by generated text.

## Per-service SOP qualification matrix (proposed)

| Service family | SOP review owner required | Material-specific evidence | Professional check | Release state |
|---|---|---|---|---|
| Haircut / Hair Styling | Qualified barber/hairdresser | Tool safety, cut zones and service constraints | hair growth/condition, multidirectional views where needed | `NOT_RELEASED` |
| Beard / Men's Grooming | Qualified grooming/barber specialist | approved tools and skin safety controls | skin/line/hair condition | `NOT_RELEASED` |
| Hair Color / Lightening / Correction | Qualified colorist + safety reviewer | exact product manufacturer protocol, history, compatibility | hair integrity, prior treatment, sensitivity concerns, indicated testing | `NOT_RELEASED` |
| Keratin / Chemical Smoothing | Qualified chemical-service specialist + safety | product/SDS/regional safety protocol, suitability | hair/scalp baseline and product contraindications | `NOT_RELEASED` |
| Extensions | Qualified extension specialist | technique/material and suitability | attachment zones and hair integrity | `NOT_RELEASED` |
| Makeup / Bridal | Qualified makeup specialist | product/skin compatibility and hygiene | occasion, sensitivity, sustainability, multi-service dependencies | `NOT_RELEASED` |
| Nails | Qualified nail specialist + hygiene/safety | material protocol and sanitation | nail condition, service limits, allergy and irritation concerns | `NOT_RELEASED` |
| Skin / Facial Advisory | Qualified nonmedical beauty specialist + medical-boundary reviewer | permitted cosmetic-only scope | no disease diagnosis or medical treatment selection | `NOT_RELEASED` |

For each service: `SPECIFIED → SOP_REVIEWED → EVIDENCE_RULES_VALIDATED → TECHNICAL_TESTED → SPECIALIST_REVIEWED → RELEASED`. No feature flag may skip a transition.

## Required Technical Plan version identity

`{tenant_id,client_session_id,selected_look_version_id,service_id,baseline_evidence_ids,sop_version,materials_protocol_refs,plan_version,specialist_id,policy_decision,validation_timestamp}`.

Changes to material input, evidence, SOP, service, chosen LookVersion or plan invalidate the corresponding validation unless a qualified reviewer explicitly concludes the change is immaterial and records the reasoning.

## Hard stop / partial modes

- Missing chemistry history or manufacturer-approved treatment parameters: `REQUIRES_PROFESSIONAL_CHECK`; omit actionable chemical ratios/times/concentrations, never guess.
- Suspected injury, dermatologic/medical symptoms or serious sensitivity: stop affected advice and escalate to appropriate qualified professional, not a medical diagnosis.
- Service outside salon skill/material inventory: disclose limitation and withhold execution authorization.
- No qualified SOP owner or evidence: advice-only preview may remain available if safe, but technical step execution remains blocked.
- Every conditional plan clearly marks unknowns, prerequisite checks, stop conditions, alternatives and responsibilities.

## Review and approval record

Qualified professional must review domain-specific hard limits, checklists and safety tiers, provide identity/qualification role, scope, exact artifact version SHA, decision, conditions and test obligations; Security verifies auth/approval integrity; QA verifies negative cases. No signoff is currently available; `G-00` remains blocked.
