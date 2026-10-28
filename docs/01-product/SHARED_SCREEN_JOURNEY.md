# In-Salon Shared-Screen User Journey

Document: `ABC-UX-001` | specialist controls workflow, client participates on the SAME screen.

## Screens and role boundaries

- **Shared:** clear consent notice, requested look, client-compatible explanations, before/after, variants, compare, selected look, relevant high-level feasibility caveats.
- **Specialist:** technical protocols, privileged observations, source evidence, steps, materials and checks, professional validation. Specialist-only information must not accidentally appear on a customer-visible display. Authorization is on the backend, never merely a hidden drawer.
- **Management:** calendar, POS, analytics, personal records, team and configuration; separate authorized view.

## End-to-end flow and owners

| Stage | Actor | State | Result | Exceptions |
|---|---|---|---|---|
| 1 Start session | Specialist | CREATED | Session ID, branch and optional appointment | No authenticated specialist → deny |
| 2 Consent | Both | CONSENTED | Scope / timestamp / retention preferences | Consent absent → no photo processing |
| 3 Select service/goal | Both | INTENT_DEFINED | REQUEST v1 | Unsupported service → bounded explanation |
| 4 Adaptive questioning | ABC + both | INPUTS_COLLECTING | Question/answer evidence; critical gaps | Conflicting preference → targeted question |
| 5 Capture pictures | Specialist | INPUT_READY | Client and reference assets with roles | Bad angle or lighting → retake/limited path |
| 6 Analyze | Engines | ANALYZED | Service-specific evidence | Safety notice, missing evidence |
| 7 Recommend | Engines | OPTIONS_READY | Valid best-fit/alternative/bolder as applicable | Only 1 valid → do not fabricate 3 |
| 8 Visualize | Engines | PREVIEW_REVIEW | QA-passed versions or honest limitation | Failed QA → reject/retry/fallback |
| 9 Refine and compare | Both | REVISION_REQUESTED | Immutable version graph, selected candidate | Lock violation → reject |
| 10 Lock selected look | Specialist + client | LOOK_SELECTED | selected_look_version_id | Not physically approved |
| 11 Feasibility | Specialist | FEASIBILITY_REVIEW | Need-for-checks, feasibility record | Unknown required facts → conditional/blocked |
| 12 Technical planning | Engines | PLAN_DRAFTED | SOP-grounded conditional steps | No approved SOP → advisory only |
| 13 Review / validate | Specialist | SPECIALIST_REVIEW | VALIDATED / CONDITIONAL / REJECTED | Altered look invalidates validation |
| 14 Operations handoff | Authorized staff | HANDOFF | Approved workflow actions | Inventory or appointment conflict → explicit failure |
| 15 Close | Specialist | CLOSED | Minimal, accurate session summary | Can close without selection |

## Non-happy paths

Interruption, partial image suitability, no reference, conflicting constraints, insufficient chemical history, S2/S3 safety escalation, unreachable generation provider, jobs completing out-of-order, disconnected UI, client changes mind, role switch, no inventory, appointment cancellation, validation revocation, consent withdrawal. Each must have a defined state transition and an E2E test.

## Explicitly excluded from product journey

No at-home user experience; no public share or automatically sending customer visuals. Download/share controls in design references translate to internal authorized work order, protected print or internal handoff only.
