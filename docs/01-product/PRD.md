# Product Requirements — ABC-PRD-2026-001

Status: `PROPOSED`; Owner: Product + Engineering; primary operation: in-person shared screen.

## Problem and outcome

Customers may not clearly specify desired aesthetics; verbal reference can be ambiguous; style pictures do not prove real-world feasibility; a preview does not give a technical plan; consultation is often disconnected from salon operations. ABC makes goal, evidence, look, visual approximation, conditional feasibility, professional plan, sign-off and operational handoff explicit and traceable.

## 20 contractual requirements

| ID | Requirement | Acceptance statement | Owner | Test |
|---|---|---|---|---|
| PRD-001 | Durable session state | Session persists and recovers from authorized checkpoint | ENG-01 | SES-01 |
| PRD-002 | Consent before image processing | No processing without valid scoped consent | Consent | SEC-02 |
| PRD-003 | Client/reference provenance | Each asset carries source and role | ENG-03 | INP-01 |
| PRD-004 | Image quality before analysis | Quality state and retake path | ENG-03 | INP-02 |
| PRD-005 | Service-bounded analysis | Only relevant attributes activated | ENG-04 | ANA-01 |
| PRD-006 | Safety/capability filtered recommendations | Invalid candidates never approved | ENG-06/14 | DEC-01 |
| PRD-007 | Structured look independent of image | Recover look without preview bytes | ENG-07 | LOOK-01 |
| PRD-008 | Locked-region preservation | Excluded pixels unchanged in canonical frame | ENG-10 | VIS-02 |
| PRD-009 | Visual QA release gate | No failed output selected as QA-approved | ENG-11 | VIS-01 |
| PRD-010 | Accepted-state preservation | Scoped edit does not silently destroy other accepted work | ENG-12 | VIS-04 |
| PRD-011 | Common-base compare | All options display consistent source/version | ENG-12 | VIS-05 |
| PRD-012 | Selected version immutable binding | Plan linked to selected look version | ENG-07/12 | TEC-01 |
| PRD-013 | Visual != feasible | No image PASS becomes professional confirmation | ENG-13 | TEC-02 |
| PRD-014 | SOP-evidence-grounded plan | No unsupported procedural parameters | ENG-15 | TEC-03 |
| PRD-015 | Specialist final validation | Approval attribution, scope and audit | ENG-16 | TEC-04 |
| PRD-016 | Invalidate superseded sign-off | Material change requires re-review | ENG-16 | TEC-05 |
| PRD-017 | Controlled business handoff | Identity and approval consistent across handoff | ENG-17 | INT-01 |
| PRD-018 | Business insight source truth | No fabricated analytics/transactions | ENG-18/19 | BUS-01 |
| PRD-019 | Backend role & tenant enforcement | Unauthorized access fails server-side | Auth | SEC-01 |
| PRD-020 | Engine observability | Trace versions, latency, reason and error | Platform | OBS-01 |

## Human authority

- Client may express preference, compare and select.
- Specialist controls the session, provides actual findings and validates execution readiness.
- Salon owner manages capability and access; ABC operator manages platform infrastructure.
- No AI agent self-grants permission or issues final specialist approval.

## Out of scope / deferred

At-home customer self-service; direct customer preview sending; autonomous physical procedures; medical diagnosis; guaranteed physical outcome; automatic stock/payment changes based on AI text; all advanced services at MVP.

## Nonfunctional requirements (NFR)

NFR-01: Durable session checkpoints, idempotent jobs, observable fail states. NFR-02: Isolated tenants and server-side RBAC. NFR-03: Purpose-limited image consent and retention. NFR-04: Empirically calibrated visual fidelity / latency / quality thresholds, not fabricated targets. NFR-05: Accessible RTL/LTR shared-display desktop/touch experience. NFR-06: Versioned models/prompts/SOPs and reproducible audit. NFR-07: Ability to pause, cancel and resume long-running AI work; separate UI responsiveness from model latency. NFR-08: All financial analytics trace to real events.

## Release priority

AI Studio `P0`; adaptive consultation, visual QA and technical planning `P0`. Operations core `P1` for pilot; optional marketing/advanced POS `P2` until later. Every feature remains in product inventory despite phased delivery.
