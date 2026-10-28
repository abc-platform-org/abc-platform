# WP-000-02 — Architecture Decision Review Dossier

**Status: PROPOSED_FOR_REVIEW.** ADR texts in `docs/00-governance/adrs/` are amended for more rigorous review, NOT marked `ACCEPTED`. The ten user-level product directives are not interpreted as authorization to invent named staff signoffs or untested performance claims.

| ADR | Product/engineering choice | Alternatives evaluated / rejected provisionally | Critical consequence | Gate / reviewer |
|---|---|---|---|---|
| ADR-001 | Independent modular application with bounded engines | A: GPT-only (cannot enforce backend authorization/durable state); B: microservices per engine (premature infra complexity) | module contracts with isolated heavy CV workers; tests before 'engine built' | Product + Architecture, G-00/G-01 |
| ADR-002 | Specialist-operated *single-screen* shared session with private specialist controls | Separate client home app (contradicts scope); unrestricted drawer (privacy risk) | role screen isolation, joint UX, local consent and selection | Product + Security/UX, G-00/G-06 |
| ADR-003 | LookSpec separate from generated image bytes | Image-only state (cannot support reliable versioned planning) | immutable LookVersion and identity of chosen model | Product + Data, G-01 |
| ADR-004 | Multi-stage service-aware visual pipeline | Pure prompt-only image editing (not reliable region locking); strict compositor *alone* (not full 3D/geometry guarantee) | CV POC mandatory per service/transform | Vision + QA, G-03 |
| ADR-005 | Independent Visual QA gate | Only model self-rating (not independently auditable); beauty score without identity check | per-class calibration/experts, no invented numeric thresholds | QA/Vision, G-03 |
| ADR-006 | Version graph and stale-job rejection | Re-generate from latest text (destroys accepted state) | immutable event and asset lineage | Platform, G-03 |
| ADR-007 | Feasibility separate from appearance | QA-passed preview => executable service (unsafe) | FZ levels and explicit uncertainty | Specialist/Safety, G-05 |
| ADR-008 | SOP/evidence-bound conditional plan with human validation | LLM freeform instructions (hallucination); auto-authorized execution (unsafe) | SOP ownership and plan version-bounded approval | Specialist + Safety, G-00/G-05 |
| ADR-009 | Persisted durable event-oriented workflow | Browser-only state / LLM conversation memory | failure recovery, idempotent actions, outbox and trace | Platform/Security, G-00/G-06 |
| ADR-010 | Tenant/role/privacy and evaluation from foundation | Frontend-only role locks; deferred QA/privacy | tests and controls from platform foundation | Security/QA, G-00/G-09 |

## Implementation pattern: modularity ≠ microservice count

Separate logical engines via typed contracts and unit/evaluation boundaries now; choose physical process/service separation based on actual model/GPU isolation, resilience, data security, traffic and cost measurements. Never build a monolithic prompt masquerading as a modular runtime.

## Inter-ADR conflict rules

- ADR-001/009 own *runtime*, not permission to execute financial or chemical procedures.
- ADR-002/010 own screen privacy and authorization; visual content remains gated by ADR-004/005.
- ADR-003/006 own version identity; ADR-007/008 must bind their results to those exact versions.
- ADR-005 authorizes only `VisualQAReport`, NOT professional service feasibility.
- ADR-008 cannot bypass safety/medical boundaries or the backend policy owned under ADR-010.

## Approval must include

Reviewer name/role; date; ADR file SHA; explicit disposition `ACCEPTED`, `REJECTED` or `REVISE`; consequence/alternative comments; linked issues; source-exception decision; and phase/contract review obligations. A single generic 'looks good' is insufficient for high-risk professional service and privacy controls.
