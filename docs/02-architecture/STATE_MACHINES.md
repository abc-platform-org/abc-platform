# State Machines — ABC-STATE-001

## Consultation session

`CREATED → CONSENTED → INTENT_DEFINED → INPUTS_COLLECTING → INPUT_READY → ANALYZED → OPTIONS_READY → PREVIEW_REVIEW ↔ REVISION_REQUESTED → LOOK_SELECTED → FEASIBILITY_REVIEW → PLAN_DRAFTED → SPECIALIST_REVIEW → HANDOFF → CLOSED`.

Side transitions: `PAUSED`, `CANCELLED`, `NEEDS_CLARIFICATION`, `SAFETY_BLOCKED`, `FAILED_RECOVERABLE`, `CLOSED_WITHOUT_DECISION`. Transitions validated by backend. Image jobs are not synchronous state writes and cannot bypass expected version. Specialist review transitions only through authenticated actor.

## Visual job

`SUBMITTED → VALIDATING_INPUT → SEGMENTING → GENERATING → COMPOSITING → QA_CHECKING → QA_PASSED | NEEDS_REVISION | QA_FAILED | CANCELLED | RETRYABLE_FAILURE`.

No preview without corresponding quality result and provenance. An outstanding job that references a superseded look version is preserved only for diagnostic history and not made current.

## Technical plan

`LOOK_SELECTED → PLAN_REQUESTED → EVIDENCE_CHECK → AWAITING_SPECIALIST_INPUT | SUFFICIENT_FOR_DRAFT → PLAN_DRAFTED → SPECIALIST_REVIEW → VALIDATED | CONDITIONALLY_VALIDATED | NEEDS_REVISION | REJECTED`.

Any material change of look, SOP, evidence or salon capability transitions validated plan to `REVIEW_REQUIRED`; never silently relabel old approval.

## Service release maturity

`SPECIFIED → CONTRACTED → IMPLEMENTED → TESTED → PROFESSIONALLY_REVIEWED → RELEASED`. `RETIRED` and `BLOCKED` allowed. The launch UI must not advertise unsupported services as released.

## Business action

`PROPOSED → AUTHORIZED → PREVIEWED → APPROVED_IF_REQUIRED → EXECUTING → CONFIRMED | FAILED | COMPENSATION_REQUIRED`. Approval never implied by chat suggestion.

## Orchestration consistency

Every state transition records actor, input/output IDs, aggregate version, event ID, timestamp and causality. Repeat requests are safe via idempotency keys. Test transition table for forbidden jumps, concurrent updates, cross-tenant actor, consent expiry and stale approval.
