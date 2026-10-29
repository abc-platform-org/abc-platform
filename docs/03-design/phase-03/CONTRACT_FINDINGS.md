# Phase-03 downstream contract findings

## CR-03-001 — Change of mind after selected look (HIGH, ADDITIVE PROPOSAL IMPLEMENTED IN PROTOTYPE)
Evidence: accepted CONSULTATION_SESSION transitions include PREVIEW_REVIEW → REVISION_REQUESTED → PREVIEW_REVIEW, but no return from LOOK_SELECTED / FEASIBILITY_REVIEW / PLAN_DRAFTED / SPECIALIST_REVIEW to revision. Phase-01 SESSION_JOURNEYS_AND_FAILURES explicitly requires changing mind after lock and invalidating plan/approval dependencies.

Proposed resolution for contract review: server command bound to expected_state_version and idempotency key creates a new revision branch from selected LookVersion, atomically invalidates downstream feasibility/plan/validation as appropriate, cancels superseded jobs, emits version-bound events and enters REVISION_REQUESTED. Receipt-bearing handoffs need explicit cancellation/compensation policy; never silently reverse a committed business effect.

No accepted contract has been edited in this Phase-03 change. A separate contracts/phase03/revision-transition-addendum.json explicitly proposes the missing transition and invalidation semantics. The prototype demonstrates this proposal with negative tests. Backend adoption and final contract reconciliation remain review items; this is not silently presented as an existing v1 operation.

## CR-03-002 — State-name drift in prose (MEDIUM, RESOLVED FOR DESIGN)
Older product prose says CLOSED_NO_SELECTION, SESSION_INITIALIZED or CONSULTING. Current executable source uses CLOSED_WITHOUT_DECISION, CREATED, INPUTS_COLLECTING. Screen mapping and tests use exact current contract states. Historical text remains unchanged; migration aliases must not be sent as server enum values.

## UX-03-003 — Pending job pause race (MEDIUM, FIXED IN PROTOTYPE)
Pausing during generation could leave a stale pending marker after the simulated result was rejected. Pause now cancels the pending fixture and increments job identity. Resume retains last valid workflow state and permits retry. Negative test covers the race.

## Evidence limits
Six historical visual references unresolved; advanced image operations (multi-view, palette, actual reference transfer) and full management screens remain specification-only. The length-variation prototype is not a substitute for their complete interactive coverage. Hosted publication did not return a usable project identity and subsequent owned-site listing showed no matching new site; no public/private deployment is claimed.


## Decision update — 2026-10-29

CR-03-001 has been accepted under delegated **Phase-03 synthetic design authority only**, using the detailed guards and failure policy in `contracts/phase03/revision-transition-addendum.json`. Adoption by a real backend or by frozen `contracts/v1` remains prohibited without a separate versioned contract change and concurrency/idempotency review. Existing historical proposal language above is preserved as its initial assessment.

Newly discovered and corrected synthetic issues: conflicting image/text-only consent paths and shared-display exposure of handoff receipt details. Regressions are in `tests/phase03/model.test.mjs` and `tests/phase03/browser.spec.mjs`. Browser evidence does not certify real authorization or images.
